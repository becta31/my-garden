import os
import requests
import re
import ast
from datetime import datetime
from openai import OpenAI


def get_ai_advice(plants, today_list, weather_data):
    hf_token = os.getenv("HF_API_TOKEN", "").strip()
    if not hf_token:
        return "⚠️ Добавьте HF_API_TOKEN в секреты GitHub."

    client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=hf_token)

    # Уличная погода (Москва)
    out_temp = weather_data.get("temp", 0)
    out_hum = weather_data.get("hum", 50)
    out_desc = weather_data.get("desc", "нет данных")

    # Фикс-контекст квартиры (твой реальный)
    indoor_context = (
        "КВАРТИРА (фикс): температура зимой не ниже 23°C; влажность 25–35%; отопление. "
        "Запрещено советовать 'согреть комнату' или паниковать из-за минуса на улице. "
        "Уличная погода влияет только на риски: холодное стекло/сквозняк при проветривании/резкие перепады."
    )

    # Краткая структура коллекции (чтобы ИИ не путал группы)
    plants_brief = "\n".join(
        [
            f"- {p.get('name','?')} | cat={p.get('category','?')} | loc={p.get('location','-')} | waterFreq={p.get('waterFreq','?')}"
            for p in plants
        ]
    )

    today_brief = ", ".join(today_list) if today_list else "сегодня по расписанию полива нет"

    # --- АГЕНТ 1 (Llama): агроном по погоде ---
    system_agro = (
        "Ты агроном по домашней коллекции растений. "
        "Учитывай уличную погоду как фактор риска (сквозняк, холодное стекло, пасмурность), "
        "но НЕ давай бытовые советы и НЕ повторяй очевидности. "
        "Запрещено: универсальные советы 'опрыскивать всё'. "
        "Для кактусов и адениумов: НЕ опрыскивать. "
        "Формат: 3–5 буллетов, каждый максимум 12–14 слов, без вступлений."
    )

    user_agro = (
        f"{indoor_context}\n"
        f"УЛИЦА (Москва): {out_temp}°C, {out_hum}%, {str(out_desc).capitalize()}.\n\n"
        f"Коллекция:\n{plants_brief}\n\n"
        f"Сегодня по плану: {today_brief}.\n\n"
        "Дай рекомендации по уходу на сегодня с учётом уличной погоды как риска."
    )

    advice_llama = "• Проветривание делай коротко, избегай холодного стекла у подоконника."
    try:
        res1 = client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[
                {"role": "system", "content": system_agro},
                {"role": "user", "content": user_agro},
            ],
            max_tokens=160,
            temperature=0.4,
            timeout=12,
        )
        advice_llama = res1.choices[0].message.content.strip().replace("*", "")
    except Exception as e:
        print(f"Ошибка Llama: {e}")

    # --- АГЕНТ 2 (Qwen): профессор-ревизор ---
    system_prof = (
        "Ты профессор-ревизор. Убери опасные или банальные советы. "
        "Запрещено: 'греть комнату', паника из-за уличного минуса, "
        "опрыскивание кактусов/адениумов. "
        "Сократи и сделай точнее. Формат: 3–5 буллетов, без вступлений."
    )

    user_prof = (
        f"{indoor_context}\n"
        f"УЛИЦА (Москва): {out_temp}°C, {out_hum}%, {str(out_desc).capitalize()}.\n"
        f"Сегодня по плану: {today_brief}.\n\n"
        f"Черновик агронома:\n{advice_llama}\n\n"
        "Верни финальные рекомендации."
    )

    try:
        res2 = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[
                {"role": "system", "content": system_prof},
                {"role": "user", "content": user_prof},
            ],
            max_tokens=180,
            temperature=0.3,
            timeout=18,
        )
        advice_qwen = res2.choices[0].message.content.strip().replace("*", "")
        return f"👨‍🌾\n{advice_llama}\n\n🎓\n{advice_qwen}"
    except Exception as e:
        print(f"Ошибка Qwen: {e}")
        return f"👨‍🌾\n{advice_llama}\n\n🎓\n(Профессор занят)"


def get_weather():
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    city = os.getenv("CITY_NAME", "Moscow").strip()
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url, timeout=10).json()
        return {
            "temp": round(res["main"]["temp"]),
            "hum": res["main"]["humidity"],
            "desc": res["weather"][0]["description"],
        }
    except:
        return {"temp": 0, "hum": 50, "desc": "нет данных"}


def get_tasks():
    weather = get_weather()

    try:
        with open("data.js", "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r"const\s+plantsData\s*=\s*(\[.*\]);", content, re.DOTALL)
        clean_js = re.sub(r"//.*", "", match.group(1))
        plants = ast.literal_eval(clean_js)

        now = datetime.now()
        day, month_idx = now.day, now.month - 1

        # Кто сегодня по плану полива (для контекста ИИ)
        today_list = []
        for p in plants:
            if day % p.get("waterFreq", 99) == 0:
                today_list.append(p.get("name", "?"))

        ai_advice = get_ai_advice(plants, today_list, weather)

        # Формирование сообщения
        msg = f"🌿 *ПЛАН САДА — {now.strftime('%d.%m')}*\n"
        msg += f"🌡 Улица: {weather['temp']}°C | 💧 {weather['hum']}% | {weather['desc'].capitalize()}\n\n"
        msg += f"🤖 *РЕКОМЕНДАЦИИ ПО ПОГОДЕ:*\n_{ai_advice}_\n"
        msg += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"

        tasks_count = 0
        for p in plants:
            if day % p.get("waterFreq", 99) == 0:
                tasks_count += 1
                msg += f"📍 *{p['name'].upper()}*\n"

                task_line = "💧 Полив"
                if month_idx in p.get("feedMonths", []):
                    if p.get("waterFreq", 1) > 1 or day in [1, 15]:
                        feed_info = p.get("feedNote", "Удобрение")
                        task_line += f" + 🧪 *{feed_info}*"

                msg += f"{task_line}\n"

                if "warning" in p:
                    short_warn = p["warning"].replace("Мороз за окном! ", "❄️ ")
                    msg += f"└ _{short_warn}_\n"

                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"

        if tasks_count > 0:
            msg += f"\n✅ *Всего к поливу: {tasks_count}*"
        else:
            msg += "\n🌿 *Сегодня по расписанию только отдых!*"

        return msg

    except Exception as e:
        return f"Ошибка парсинга базы: {e}"


def send_to_telegram(text):
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": [[{"text": "✅ Сделано!", "callback_data": "done"}]]},
    }
    try:
        requests.post(url, json=payload, timeout=12)
    except:
        pass


if __name__ == "__main__":
    send_to_telegram(get_tasks())

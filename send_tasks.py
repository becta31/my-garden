import os
import requests
import re
import ast
import json
from datetime import datetime


LAST_WEATHER_FILE = "last_weather.json"


def load_last_temp():
    try:
        with open(LAST_WEATHER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("temp")
    except Exception:
        return None


def save_last_temp(temp, city="Moscow"):
    try:
        with open(LAST_WEATHER_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"temp": temp, "city": city, "saved_at": datetime.now().isoformat()},
                f,
                ensure_ascii=False
            )
    except Exception:
        pass


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
            "wind": res.get("wind", {}).get("speed", 0),
        }
    except Exception:
        return {"temp": 0, "hum": 50, "desc": "нет данных", "wind": 0}


def weather_comment(weather, month_idx, delta_temp=None):
    """
    1 строка, только если есть триггер.
    Москва, годовой режим + резкие качели (delta >= 8°C).
    """
    temp = weather.get("temp", 0)
    wind = weather.get("wind", 0)

    # 0) Качели температуры (самое полезное весной/осенью)
    if delta_temp is not None and abs(delta_temp) >= 8:
        if delta_temp > 0:
            return f"📈 Резкое потепление (+{abs(delta_temp)}°). Не форсируй изменения ухода за один день."
        else:
            return f"📉 Резкое похолодание (−{abs(delta_temp)}°). Без резких действий, проветривание аккуратно."

    # 1) Очень сильный ветер — круглый год
    if wind >= 12:
        return "🌬 Очень сильный ветер. Проветривай коротко, избегай сквозняка у окон."

    # ЗИМА: Дек–Фев
    if month_idx in [11, 0, 1]:
        if temp <= -15:
            return "🥶 Сильный мороз. Окна открывай кратко; избегай холодного стекла у растений."
        if temp <= -10:
            return "❄️ Мороз. Проветривание делай коротко, без сквозняка."
        if wind >= 9:
            return "🌬 Ветер. При проветривании избегай прямого потока на подоконник."
        return None

    # ВЕСНА: Мар–Май
    if month_idx in [2, 3, 4]:
        if month_idx in [2, 3] and temp <= -2:
            return "⚠️ Возврат холода. Не форсируй сезонные изменения ухода."
        if month_idx == 2 and temp >= 12:
            return "🌤 Раннее потепление. Переход к весеннему режиму делай постепенно."
        if month_idx in [3, 4] and temp >= 20:
            return "🌤 Резкое тепло. Не меняй уход резко: делай переход плавно."
        if wind >= 9:
            return "🌬 Ветреный день. Проветривай аккуратно, избегай сквозняка."
        return None

    # ЛЕТО: Июн–Авг
    if month_idx in [5, 6, 7]:
        if temp >= 32:
            return "☀️ Сильная жара. Проверяй пересыхание субстрата чаще обычного."
        if temp >= 28:
            return "☀️ Жарко. Полив ориентируй по субстрату, не по календарю."
        return None

    # ОСЕНЬ: Сен–Ноя
    if month_idx in [8, 9, 10]:
        if month_idx == 8 and temp <= 6:
            return "🍂 Раннее похолодание. Переход к более спокойному режиму делай постепенно."
        if month_idx in [9, 10] and temp <= 0:
            return "🍂 Первый минус. Сокращай активные действия по уходу постепенно."
        if wind >= 9:
            return "🌬 Ветер. Проветривай коротко, избегай сквозняка у окон."
        return None

    return None


def get_tasks():
    weather = get_weather()
    city = os.getenv("CITY_NAME", "Moscow").strip()

    try:
        with open("data.js", "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r"const\s+plantsData\s*=\s*(\[.*\]);", content, re.DOTALL)
        clean_js = re.sub(r"//.*", "", match.group(1))
        plants = ast.literal_eval(clean_js)

        now = datetime.now()
        day, month_idx = now.day, now.month - 1

        # Дельта температуры к "вчера"
        last_temp = load_last_temp()
        delta_temp = None
        if last_temp is not None:
            try:
                delta_temp = int(weather.get("temp", 0)) - int(last_temp)
            except Exception:
                delta_temp = None

        comment = weather_comment(weather, month_idx, delta_temp=delta_temp)

        # Формирование сообщения
        msg = f"🌿 *ПЛАН САДА — {now.strftime('%d.%m')}*\n"
        msg += (
            f"🌡 Улица: {weather['temp']}°C | 💧 {weather['hum']}% | "
            f"{str(weather['desc']).capitalize()} | 💨 {weather.get('wind', 0)} м/с\n\n"
        )

        # Погодный комментарий: только при триггере
        if comment:
            msg += f"🤖 {comment}\n"
        else:
            msg += "🤖 Погодные корректировки не требуются.\n"

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

        # сохраняем "сегодня" для дельты завтра
        save_last_temp(weather.get("temp", 0), city=city or "Moscow")

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
    except Exception:
        pass


if __name__ == "__main__":
    send_to_telegram(get_tasks())

# send_tasks.py

import os
import json
import sys
from datetime import datetime, timezone

import requests

LAST_WEATHER_FILE = "last_weather.json"
HISTORY_FILE = "history.json"
PLANTS_FILE = "plants.json"


def md_escape(text) -> str:
    if text is None:
        return ""
    s = str(text)
    s = s.replace("\\", "\\\\")
    for char in '_*[]()~`>#+-=|{}.!':
        s = s.replace(char, f'\\{char}')
    return s


def send_to_telegram(text: str):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("ERROR: Нет токена или ID чата")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "MarkdownV2"}

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("✅ Сообщение отправлено!")
            return True
        print(f"❌ Ошибка Telegram: {response.text[:300]}")
        return False
    except Exception as e:
        print(f"❌ Исключение при отправке: {e}")
        return False


def check_file_exists(filepath):
    if not os.path.exists(filepath):
        print(f"ERROR: Файл не найден: {filepath}")
        sys.exit(1)


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return {}
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            fixed = {}
            for item in data:
                if isinstance(item, dict) and "plant_id" in item:
                    fixed[item["plant_id"]] = {"last_reminded": item.get("ts")}
            return fixed
        return {}
    except Exception as e:
        print(f"Ошибка чтения history.json: {e}")
        return {}


def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения history.json: {e}")


def get_last_event_ts(entry: dict):
    if not isinstance(entry, dict):
        return None
    return entry.get("last_reminded") or entry.get("last_watered")


def days_since_last_reminder(plant_id: str, history: dict) -> int:
    entry = history.get(plant_id, {})
    last = get_last_event_ts(entry)
    if not last:
        return 999
    try:
        now = datetime.now(timezone.utc)
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        return (now - last_dt).days
    except Exception as e:
        print(f"Ошибка расчёта дней для {plant_id}: {e}")
        return 999


def load_plants():
    try:
        with open(PLANTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            plants = data.get("plants", [])
            if not plants:
                print("WARNING: plants.json — словарь без ключа 'plants'")
            return plants
        return []
    except Exception as e:
        print(f"ERROR: plants.json не загружен — {e}")
        return []


def load_last_temp():
    try:
        with open(LAST_WEATHER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("temp") if isinstance(data, dict) else None
    except Exception:
        return None


def save_last_temp(temp):
    if temp is None:
        return
    try:
        with open(LAST_WEATHER_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"temp": temp, "saved_at": datetime.now(timezone.utc).isoformat()},
                f,
                ensure_ascii=False
            )
    except Exception as e:
        print(f"Ошибка сохранения last_weather.json: {e}")


def get_weather():
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    city = os.getenv("CITY_NAME", "Moscow").strip() or "Moscow"

    if not api_key:
        return {
            "available": False,
            "temp": None,
            "hum": None,
            "desc": "нет данных",
            "wind": None,
            "city": city,
        }

    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={api_key}&units=metric&lang=ru"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        res = response.json()

        if not isinstance(res, dict):
            raise ValueError("Некорректный ответ API")

        return {
            "available": True,
            "temp": round(res.get("main", {}).get("temp", 0)),
            "hum": int(res.get("main", {}).get("humidity", 0)),
            "desc": res.get("weather", [{}])[0].get("description", "нет данных"),
            "wind": float(res.get("wind", {}).get("speed", 0)),
            "city": city,
        }
    except Exception as e:
        print(f"Ошибка погоды: {e}")
        return {
            "available": False,
            "temp": None,
            "hum": None,
            "desc": "нет данных",
            "wind": None,
            "city": city,
        }


def get_season(month: int) -> str:
    return {
        12: "Зима", 1: "Зима", 2: "Зима",
        3: "Весна", 4: "Весна", 5: "Весна",
        6: "Лето", 7: "Лето", 8: "Лето",
        9: "Осень", 10: "Осень", 11: "Осень",
    }[month]


def feeding_active(plant: dict, month: int) -> bool:
    feed_months = plant.get("feedMonths")
    if not feed_months:
        return True
    if not isinstance(feed_months, list):
        return False

    allowed = set()
    for m in feed_months:
        try:
            mi = int(m)
        except Exception:
            continue
        if 1 <= mi <= 12:
            allowed.add(mi)

    if not allowed:
        return False
    return month in allowed


def get_ai_advice(weather, plant_names, month):
    try:
        from cerebras.cloud.sdk import Cerebras
    except ImportError:
        print("⚠️ Библиотека 'cerebras-cloud-sdk' не установлена. Проверьте requirements.txt")
        return None

    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        print("⚠️ CEREBRAS_API_KEY не найден.")
        return None

    if not weather.get("available"):
        return None

    season = get_season(month)
    plants_list = ', '.join(plant_names) if plant_names else 'nobody'

    print("🧠 Запрашиваю совет у Cerebras (Llama 3.1)...")

    try:
        client = Cerebras(api_key=api_key)

        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты — профессиональный агроном. Твоя задача — дать ОДИН короткий совет "
                        "(до 150 символов) на русском языке для КОМНАТНЫХ растений. "
                        "Учитывай погоду на улице (холодный подоконник, сквозняки, яркость солнца). "
                        "Пиши просто."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Погода на улице: {weather['temp']}°C, влажность {weather['hum']}%. "
                        f"Сезон: {season}. Растения на поливе: {plants_list}."
                    )
                }
            ],
            model="llama3.1-8b",
            max_completion_tokens=100,
            temperature=0.5,
            stream=False
        )

        text = completion.choices[0].message.content
        clean_text = text.strip().replace('*', '').split('\n')[0]

        if len(clean_text) > 160:
            clean_text = clean_text[:157] + "..."

        if clean_text:
            print(f"✅ Совет получен: {clean_text}")
            return clean_text
        print("⚠️ ИИ вернул пустой текст.")
    except Exception as e:
        print(f"❌ Исключение при запросе к Cerebras: {e}")

    return None


def weather_comment_fallback(weather, month, delta_temp=None):
    if not weather.get("available"):
        return "Погода недоступна — ориентируйся на сухость грунта и состояние листьев."

    temp = weather.get("temp", 0)
    wind = weather.get("wind", 0)

    if delta_temp is not None and abs(delta_temp) >= 8:
        direction = "потепление" if delta_temp > 0 else "похолодание"
        return f"Резкое {direction} ({delta_temp:+}°C)."

    if wind >= 12:
        return "Сильный ветер — растения теряют влагу быстрее."

    if month in (3, 4, 5):
        if temp < 5:
            return "Холодно. Поливай только тёплой водой."
        return "Весна! Постепенно увеличивай полив."

    return None


def build_weather_line(weather):
    if not weather.get("available"):
        return f"🌡 {md_escape('Погода: нет данных')}\n"
    return f"🌡 {md_escape(str(weather['temp']))}°C \\| 💧 {md_escape(str(weather['hum']))}%\n"


def main():
    check_file_exists(PLANTS_FILE)

    plants = load_plants()
    if not plants:
        print("ERROR: Список растений пуст.")
        return

    history = load_history()
    weather = get_weather()
    last_temp = load_last_temp()

    current_temp = weather.get("temp")
    delta_temp = None
    if current_temp is not None and last_temp is not None:
        delta_temp = current_temp - last_temp

    save_last_temp(current_temp)

    now_utc = datetime.now(timezone.utc)
    month = now_utc.month
    today_str = now_utc.strftime('%d.%m')

    text_parts = [f"🌿 *ПЛАН САДА — {md_escape(today_str)}*\n"]
    text_parts.append(build_weather_line(weather))

    plants_to_remind = []
    plants_to_remind_names = []

    for p in plants:
        if not isinstance(p, dict):
            continue

        plant_id = p.get("id", p.get("name", "unknown"))
        water_freq = p.get("waterFreq", 7)
        name = p.get("name", "Без имени")

        if days_since_last_reminder(plant_id, history) < water_freq:
            continue

        plants_to_remind.append(plant_id)
        plants_to_remind_names.append(name)

        feed_short = p.get("feedShort", "")
        stage = str(p.get("stage", "")).strip().lower()

        line = f"📍 *{md_escape(name)}*\n💧 *Полив*\n"

        if stage in ("dormant", "покой"):
            line += "❄️ Режим покоя: *только вода*\n"
        elif stage in ("recover", "восстановление"):
            line += "🚑 Восстановление: без удобрений\n"
        else:
            if feed_short:
                if feeding_active(p, month):
                    line += f"🧪 _{md_escape(feed_short)}_\n"
                else:
                    line += "🧪 Сейчас не сезон внесения удобрений\n"

        text_parts.append(line + "\n")

    if plants_to_remind:
        tip = get_ai_advice(weather, plants_to_remind_names, month)
        if tip:
            text_parts.insert(2, f"🧠 _{md_escape(tip)}_\n")
        else:
            comment = weather_comment_fallback(weather, month, delta_temp)
            if comment:
                text_parts.insert(2, f"🤖 _{md_escape(comment)}_\n")
    else:
        text_parts.append("✅ Полив никому не требуется\\. Отдыхаем\\!")

    message = "".join(text_parts)

    if send_to_telegram(message):
        now_iso = now_utc.isoformat()
        for pid in plants_to_remind:
            if pid not in history or not isinstance(history[pid], dict):
                history[pid] = {}
            history[pid]["last_reminded"] = now_iso
            history[pid].pop("last_watered", None)

        save_history(history)
        print(f"✅ Готово. Обновлено растений: {len(plants_to_remind)}.")
    else:
        print("❌ Сообщение не отправлено. История не обновлялась.")


if __name__ == "__main__":
    main()

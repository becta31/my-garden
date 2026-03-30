# send_tasks.py

import os
import json
import sys
from datetime import datetime, timezone

import requests

LAST_WEATHER_FILE = "last_weather.json"
HISTORY_FILE = "history.json"
FEED_HISTORY_FILE = "feed_history.json"
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
        print(f"❌ Ошибка Telegram: {response.text[:500]}")
        return False
    except Exception as e:
        print(f"❌ Исключение при отправке: {e}")
        return False


def check_file_exists(filepath):
    if not os.path.exists(filepath):
        print(f"ERROR: Файл не найден: {filepath}")
        sys.exit(1)


def load_json_file(filepath, default):
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, type(default)) else default
    except Exception as e:
        print(f"Ошибка чтения {filepath}: {e}")
        return default


def save_json_file(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения {filepath}: {e}")


def load_history():
    data = load_json_file(HISTORY_FILE, {})
    if isinstance(data, dict):
        return data
    return {}


def save_history(history):
    save_json_file(HISTORY_FILE, history)


def load_feed_history():
    data = load_json_file(FEED_HISTORY_FILE, {})
    if isinstance(data, dict):
        return data
    return {}


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
        print(f"Ошибка сохранения {LAST_WEATHER_FILE}: {e}")


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
            return "Холодно — поливай только тёплой водой."
        return "Весна — постепенно увеличивай полив."

    return None


def build_weather_line(weather):
    if not weather.get("available"):
        return f"🌡 {md_escape('Погода: нет данных')}\n"
    return f"🌡 {md_escape(str(weather['temp']))}°C \\| 💧 {md_escape(str(weather['hum']))}%\n"


def parse_iso_dt(value: str):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def feeding_allowed_by_stage(stage: str) -> bool:
    stage = str(stage or "").strip().lower()
    return stage not in ("dormant", "покой", "recover", "восстановление")


def check_condition(plant: dict, cond: str) -> bool:
    flags = plant.get("flags", {}) if isinstance(plant.get("flags"), dict) else {}
    cond = str(cond or "").strip().lower()

    if cond == "buds":
        return bool(flags.get("buds", False))
    if cond == "flower_spike":
        return bool(flags.get("flower_spike", False))
    if cond == "active_growth":
        return bool(flags.get("active_growth", True))

    return True


def get_feed_status(plant: dict, feed: dict, feed_history: dict, now_utc: datetime):
    plant_id = plant.get("id", "unknown")
    stage = str(plant.get("stage", "")).strip().lower()
    month = now_utc.month

    feed_id = feed.get("id", "feed")
    feed_name = feed.get("name", "Подкормка")
    dose = feed.get("dose", "по инструкции")
    interval_days = int(feed.get("intervalDays", 999))
    months = feed.get("months", [])
    only_stages = [str(x).strip().lower() for x in feed.get("onlyStages", [])]
    conditions = [str(x).strip().lower() for x in feed.get("conditions", [])]

    if not feeding_allowed_by_stage(stage):
        return f"{feed_name} — сейчас нельзя, растение в режиме покоя/восстановления"

    if months and month not in months:
        return f"{feed_name} — не сезон"

    if only_stages and stage not in only_stages:
        return f"{feed_name} — не подходит для текущей стадии"

    for cond in conditions:
        if not check_condition(plant, cond):
            if cond == "buds":
                return f"{feed_name} — только если есть бутоны"
            if cond == "flower_spike":
                return f"{feed_name} — только если есть цветонос"
            return f"{feed_name} — пока не выполнены условия"

    plant_feed_history = feed_history.get(plant_id, {})
    feed_entry = plant_feed_history.get(feed_id, {}) if isinstance(plant_feed_history, dict) else {}
    last_done = parse_iso_dt(feed_entry.get("last_done"))

    if last_done is None:
        return f"{feed_name} — {dose}, можно сегодня"

    days_passed = (now_utc - last_done).days
    remaining = interval_days - days_passed

    if remaining > 0:
        return f"{feed_name} — {dose}, через {remaining} дн\\."
    return f"{feed_name} — {dose}, можно сегодня"


def build_plant_block(plant: dict, feed_history: dict, now_utc: datetime):
    name = plant.get("name", "Без имени")
    stage = str(plant.get("stage", "")).strip().lower()

    lines = [
        f"📍 *{md_escape(name)}*",
        "💧 *Полив*"
    ]

    if stage in ("dormant", "покой"):
        lines.append("❄️ Режим покоя: *только вода*")
    elif stage in ("recover", "восстановление"):
        lines.append("🚑 Восстановление: без удобрений")
    else:
        feeds = plant.get("feeds", [])
        if isinstance(feeds, list) and feeds:
            for feed in feeds:
                if not isinstance(feed, dict):
                    continue
                status = get_feed_status(plant, feed, feed_history, now_utc)
                lines.append(f"🧪 {md_escape(status)}")

    return "\n".join(lines)


def main():
    check_file_exists(PLANTS_FILE)

    plants = load_plants()
    if not plants:
        print("ERROR: Список растений пуст.")
        return

    history = load_history()
    feed_history = load_feed_history()
    weather = get_weather()
    last_temp = load_last_temp()

    current_temp = weather.get("temp")
    delta_temp = None
    if current_temp is not None and last_temp is not None:
        delta_temp = current_temp - last_temp

    save_last_temp(current_temp)

    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%d.%m")

    text_parts = [f"🌿 *ПЛАН САДА — {md_escape(today_str)}*\n"]
    text_parts.append(build_weather_line(weather))

    comment = weather_comment_fallback(weather, now_utc.month, delta_temp)
    if comment:
        text_parts.append(f"🤖 _{md_escape(comment)}_\n\n")

    plants_to_remind = []

    for plant in plants:
        if not isinstance(plant, dict):
            continue

        plant_id = plant.get("id", plant.get("name", "unknown"))
        water_freq = plant.get("waterFreq", 7)

        if days_since_last_reminder(plant_id, history) < water_freq:
            continue

        plants_to_remind.append(plant_id)
        text_parts.append(build_plant_block(plant, feed_history, now_utc))
        text_parts.append("\n\n")

    if not plants_to_remind:
        text_parts.append("✅ Полив никому не требуется\\. Отдыхаем\\!")

    message = "".join(text_parts).rstrip()

    if send_to_telegram(message):
        now_iso = now_utc.isoformat()
        for pid in plants_to_remind:
            if pid not in history or not isinstance(history[pid], dict):
                history[pid] = {}
            history[pid]["last_reminded"] = now_iso
            history[pid].pop("last_watered", None)

        save_history(history)
        print(f"✅ Готово. Напоминаний по поливу: {len(plants_to_remind)}.")
    else:
        print("❌ Сообщение не отправлено. История полива не обновлялась.")


if __name__ == "__main__":
    main()

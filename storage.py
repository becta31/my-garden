import json
import os
from datetime import datetime, timezone

LAST_WEATHER_FILE = "last_weather.json"
HISTORY_FILE = "history.json"
FEED_HISTORY_FILE = "feed_history.json"


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
    return data if isinstance(data, dict) else {}


def save_history(history):
    save_json_file(HISTORY_FILE, history)


def load_feed_history():
    data = load_json_file(FEED_HISTORY_FILE, {})
    return data if isinstance(data, dict) else {}


def save_feed_history(feed_history):
    save_json_file(FEED_HISTORY_FILE, feed_history)


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
                ensure_ascii=False,
                indent=2
            )
    except Exception as e:
        print(f"Ошибка сохранения {LAST_WEATHER_FILE}: {e}")

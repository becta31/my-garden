# send_tasks.py — ИСПРАВЛЕННАЯ ВЕРСИЯ с защитой от list/dict (март 2026)
import os
import json
import re
import logging
from datetime import datetime
import requests

logging.basicConfig(
    filename='garden.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

LAST_WEATHER_FILE = "last_weather.json"
HISTORY_FILE = "history.json"


def md_escape(text) -> str:
    """Полный экранирующий фильтр для MarkdownV2 — все спецсимволы"""
    if text is None:
        return ""
    s = str(text)
    # Сначала экранируем \, чтобы не сломать другие экраны
    s = s.replace("\\", "\\\\")
    # Полный список специальных символов MarkdownV2 (по документации Telegram)
    special = r"([_*[\]()~`>#+-=|{}.!])"
    return re.sub(special, r"\\\1", s)


def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения history: {e}")


def days_since_last_watering(plant_id: str, history: dict) -> int:
    entry = history.get(plant_id, {})
    last = entry.get("last_watered")
    if not last:
        return 999
    try:
        return (datetime.now() - datetime.fromisoformat(last)).days
    except:
        return 999


def load_plants():
    try:
        with open("plants.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                print("DEBUG: plants.json — чистый список, возвращаем как есть")
                return data
            elif isinstance(data, dict):
                plants = data.get("plants", [])
                print(f"DEBUG: plants.json — объект, найдено {len(plants)} растений")
                return plants
            else:
                print("ERROR: plants.json имеет неожиданный формат")
                return []
    except Exception as e:
        print(f"ERROR: plants.json не загружен — {e}")
        return []


def load_last_temp():
    try:
        with open(LAST_WEATHER_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("temp")
    except:
        return None


def save_last_temp(temp):
    try:
        with open(LAST_WEATHER_FILE, "w", encoding="utf-8") as f:
            json.dump({"temp": temp, "saved_at": datetime.now().isoformat()}, f, ensure_ascii=False)
    except:
        pass


def get_weather():
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    city = os.getenv("CITY_NAME", "Moscow").strip() or "Moscow"
    if not api_key:
        return {"temp": 0, "hum": 50, "desc": "нет данных", "wind": 0}
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url, timeout=10).json()
        return {
            "temp": round(res["main"]["temp"]),
            "hum": int(res["main"]["humidity"]),
            "desc": res["weather"][0]["description"],
            "wind": float(res.get("wind", {}).get("speed", 0)),
        }
    except Exception as e:
        print(f"Weather error: {e}")
        return {"temp": 0, "hum": 50, "desc": "нет данных", "wind": 0}


def weather_comment(weather, month_idx, delta_temp=None):
    temp = weather.get("temp", 0)
    wind = weather.get("wind", 0)
    if delta_temp is not None and abs(delta_temp) >= 8:
        return f"Резкое {'потепление' if delta_temp > 0 else 'похолодание'} (+{abs(delta_temp)}°). Не форсируй изменения ухода."
    if wind >= 12:
        return "Очень сильный ветер. Проветривай коротко..."
    if month_idx in (2, 3):
        if temp < 5:
            return "Холодно. Цитрусы и адениум — только тёплой водой."
        return "Весна! Можно постепенно увеличивать полив."
    return None


def stage_hint(stage):
    if not stage:
        return None
    s = str(stage).strip().lower()
    if s in ("bloom", "цветение"):
        return "Режим: цветение — PK (K>N) слабой дозой, без гуматов/янтарки."
    if s in ("foliage", "листва", "рост"):
        return "Режим: листва — умеренный рост, без резких стимуляций."
    if s in ("recover", "восстановление"):
        return "Режим: восстановление — без стимуляторов/PK, приоритет корни."
    if s in ("dormant", "покой"):
        return "Режим: покой — только вода, без подкормок."
    return None


def semi_auto_hint(p, month_idx):
    return None


def send_to_telegram(text: str):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("ERROR: Нет TELEGRAM_TOKEN или TELEGRAM_CHAT_ID")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "MarkdownV2"
    }

    print("DEBUG: === ОТПРАВКА В TELEGRAM ===")
    print(f"DEBUG: Длина текста: {len(text)}")
    print(f"DEBUG: Первые 150 символов текста:\n{text[:150]}...")

    try:
        response = requests.post(url, json=payload, timeout=15)
        print(f"DEBUG: Status code: {response.status_code}")
        print(f"DEBUG: Ответ Telegram: {response.text[:600]}")
        if response.status_code == 200:
            print("✅ Сообщение отправлено!")
            return True
        else:
            print("❌ Ошибка отправки")
            return False
    except Exception as e:
        print(f"❌ Исключение при отправке: {e}")
        return False


def main():
    try:
        plants = load_plants()
        
        # отладка сразу после загрузки — всегда печатается
        print(f"DEBUG: Загружено растений: {len(plants) if plants else 0}, тип: {type(plants)}")
        
        # дополнительная отладка каждого растения
        for i, p in enumerate(plants):
            if isinstance(p, dict):
                print(f"DEBUG: Растение {i+1}: dict с ключами {list(p.keys())}")
            else:
                print(f"DEBUG: Растение {i+1}: ЭТО НЕ СЛОВАРЬ!!! тип = {type(p)}")
        
        if not plants:
            print("❌ Нет растений")
            return
        
        history = load_history()
        weather = get_weather()
        last_temp = load_last_temp()
        delta_temp = weather["temp"] - last_temp if last_temp is not None else None
        save_last_temp(weather["temp"])
        
        month_idx = datetime.now().month - 1
        
        text_parts = [f"🌿 *ПЛАН САДА — {datetime.now().strftime('%d.%m')}*\n"]
        text_parts.append(f"🌡 {weather['temp']}°C | 💧 {weather['hum']}% | {md_escape(weather['desc'])}\n")
        
        comment = weather_comment(weather, month_idx, delta_temp)
        if comment:
            text_parts.append(f"🤖 Совет: {md_escape(comment)}\n")
        
        text_parts.append("⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n")
        
        print("DEBUG: Доходим до цикла for p in plants")

        for p in plants:
            # Отладка: проверяем тип и имя каждого растения
            print(f"DEBUG: Обрабатываем растение {p.get('name', 'без имени')}, тип p = {type(p)}")

            # Безопасное получение значений
            plant_id = p.get("id", "без id")
            water_freq = p.get("waterFreq", 7)   # по умолчанию 7 дней
            name = p.get("name", "без имени")
            feed_short = p.get("feedShort", "без подкормки")
            stage = p.get("stage")

            needs_water = days_since_last_watering(plant_id, history) >= water_freq
            stage_tip = stage_hint(stage)
            hint = semi_auto_hint(p, month_idx)

            line = f"📍 {md_escape(name)}\n"
            if needs_water:
                line += f"💧 Полив + "
            else:
                line += f"💧 Полив (через {water_freq} дней) + "
            line += f"{md_escape(feed_short)}\n"
            if stage_tip:
                line += f"└ {md_escape(stage_tip)}\n"
            if hint:
                line += f"└ {md_escape(hint)}\n"
            text_parts.append(line)
        
        full_text = "".join(text_parts)
        
        send_to_telegram(full_text)
        
        print("Задача завершена успешно")
    
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")


if __name__ == "__main__":
    main()

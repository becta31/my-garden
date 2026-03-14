# send_tasks.py — ФИНАЛЬНАЯ ВЕРСИЯ (авто-учет при отправке)
import os
import json
import logging
import sys
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
PLANTS_FILE = "plants.json"

# --- Вспомогательные функции ---

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
        print("ERROR: Нет токена или ID")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "MarkdownV2"
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("✅ Сообщение отправлено!")
            return True
        else:
            print(f"❌ Ошибка: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

def check_file_exists(filepath, description):
    if not os.path.exists(filepath):
        error_msg = f"⚠️ *Ошибка*\nФайл `{filepath}` не найден\\."
        send_to_telegram(error_msg)
        sys.exit(1)
    return True

def load_history():
    """Загружает историю. Исправляет конфликт форматов (list vs dict)."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            # Если файл пуст
            if not data:
                return {}
                
            # Если это словарь (правильный формат)
            if isinstance(data, dict):
                return data
            
            # Если это список (старый/ошибочный формат от process_updates)
            # Конвертируем его в словарь, чтобы бот не падал
            if isinstance(data, list):
                fixed_history = {}
                for item in data:
                    if isinstance(item, dict) and "plant_id" in item and "ts" in item:
                        fixed_history[item["plant_id"]] = {"last_watered": item["ts"]}
                return fixed_history
                
            return {}
    except Exception as e:
        print(f"Warning: Ошибка чтения history: {e}")
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
        with open(PLANTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("plants", [])
            return []
    except Exception as e:
        print(f"ERROR: plants.json не загружен — {e}")
        return []

def load_last_temp():
    try:
        with open(LAST_WEATHER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("temp") if isinstance(data, dict) else None
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
        if not isinstance(res, dict):
             return {"temp": 0, "hum": 50, "desc": "ошибка API", "wind": 0}
        
        return {
            "temp": round(res.get("main", {}).get("temp", 0)),
            "hum": int(res.get("main", {}).get("humidity", 0)),
            "desc": res.get("weather", [{}])[0].get("description", "нет данных"),
            "wind": float(res.get("wind", {}).get("speed", 0)),
        }
    except Exception as e:
        print(f"Weather error: {e}")
        return {"temp": 0, "hum": 50, "desc": "нет данных", "wind": 0}

def weather_comment(weather, month_idx, delta_temp=None):
    temp = weather.get("temp", 0)
    wind = weather.get("wind", 0)
    if delta_temp is not None and abs(delta_temp) >= 8:
        return f"Резкое {'потепление' if delta_temp > 0 else 'похолодание'} (+{abs(delta_temp)}°)."
    if wind >= 12:
        return "Сильный ветер."
    if month_idx in (2, 3):
        if temp < 5:
            return "Холодно. Поливай только тёплой водой."
        return "Весна! Увеличивай полив."
    return None

# --- Основная логика ---

def main():
    try:
        check_file_exists(PLANTS_FILE, "База данных")
        
        plants = load_plants()
        if not plants:
            return
        
        history = load_history()
        weather = get_weather()
        last_temp = load_last_temp()
        delta_temp = weather["temp"] - last_temp if last_temp is not None else None
        save_last_temp(weather["temp"])
        
        month_idx = datetime.now().month - 1
        today_str = datetime.now().strftime('%d.%m')
        
        # Заголовок
        text_parts = [f"🌿 *ПЛАН САДА — {md_escape(today_str)}*\n"]
        text_parts.append(f"🌡 {weather['temp']}°C \\| 💧 {weather['hum']}%\n")
        
        comment = weather_comment(weather, month_idx, delta_temp)
        if comment:
            text_parts.append(f"🤖 _{md_escape(comment)}_\n")
        
        text_parts.append("\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\n")
        
        plants_to_water_today = []

        # Анализ растений
        for p in plants:
            if not isinstance(p, dict): continue

            plant_id = p.get("id", p.get("name", "unknown"))
            water_freq = p.get("waterFreq", 7)
            name = p.get("name", "Без имени")
            feed_short = p.get("feedShort", "")
            stage = str(p.get("stage", "")).strip().lower()

            # Логика: нужно ли поливать?
            days_passed = days_since_last_watering(plant_id, history)
            needs_water = days_passed >= water_freq
            
            if not needs_water:
                continue

            plants_to_water_today.append(plant_id)
            
            # Формируем блок
            line = f"📍 *{md_escape(name)}*\n"
            line += "💧 *Полив*\n"
            
            if stage in ("dormant", "покой"):
                line += "❄️ Режим покоя: *только вода*\n"
            elif stage in ("recover", "восстановление"):
                line += "🚑 Восстановление: без удобрений\n"
            else:
                if feed_short:
                    line += f"🧪 _{md_escape(feed_short)}_\n"
            
            text_parts.append(line + "\n")
        
        # Итог
        if not plants_to_water_today:
            text_parts.append("✅ Полив никому не требуется\\. Отдыхаем\\!")
        
        full_text = "".join(text_parts)
        
        # 1. ОТПРАВКА
        if send_to_telegram(full_text):
            # 2. УЧЕТ (Логика: сообщение ушло = задание выполнено)
            # Сохраняем текущее время для всех растений из списка
            now_iso = datetime.now().isoformat()
            for pid in plants_to_water_today:
                if pid not in history:
                    history[pid] = {}
                history[pid]["last_watered"] = now_iso
            
            save_history(history)
            print(f"✅ Учтено: обновлена история для {len(plants_to_water_today)} растений.")
        else:
            print("❌ Сообщение не отправлено, история НЕ обновлена (попробуем в следующий раз).")
    
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()

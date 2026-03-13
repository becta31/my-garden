# send_tasks.py — ИСПРАВЛЕННАЯ ЛОГИКА (март 2026)
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
    """Экранирует спецсимволы для Telegram MarkdownV2"""
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
        print("ERROR: Нет TELEGRAM_TOKEN или TELEGRAM_CHAT_ID")
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
            logger.info("Сообщение отправлено в Telegram")
            return True
        else:
            print(f"❌ Ошибка Telegram: {response.text[:200]}")
            logger.error(f"Telegram error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Исключение при отправке: {e}")
        logger.error(f"Exception: {e}")
        return False

def check_file_exists(filepath, description):
    """Проверяет наличие файла. Если нет — шлет ошибку в Telegram и завершает скрипт."""
    if not os.path.exists(filepath):
        error_msg = f"⚠️ *Ошибка конфигурации*\nФайл `{filepath}` \\({md_escape(description)}\\) не найден\\."
        send_to_telegram(error_msg)
        sys.exit(1)
    return True

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
        with open(PLANTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("plants", [])
            else:
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
        return f"Резкое {'потепление' if delta_temp > 0 else 'похолодание'} (+{abs(delta_temp)}°)."
    if wind >= 12:
        return "Очень сильный ветер."
    if month_idx in (2, 3):
        if temp < 5:
            return "Холодно. Поливай только тёплой водой."
        return "Весна! Можно постепенно увеличивать полив."
    return None

# --- Основная логика ---

def main():
    try:
        # 1. Проверка файлов
        check_file_exists(PLANTS_FILE, "База данных растений")
        
        plants = load_plants()
        if not plants:
            print("❌ Список растений пуст")
            return
        
        history = load_history()
        weather = get_weather()
        last_temp = load_last_temp()
        delta_temp = weather["temp"] - last_temp if last_temp is not None else None
        save_last_temp(weather["temp"])
        
        month_idx = datetime.now().month - 1
        
        # 2. Формирование заголовка
        date_str = md_escape(datetime.now().strftime('%d.%m'))
        text_parts = [f"🌿 *ПЛАН САДА — {date_str}*\n"]
        text_parts.append(f"🌡 {weather['temp']}°C \\| 💧 {weather['hum']}% \\| {md_escape(weather['desc'])}\n")
        
        comment = weather_comment(weather, month_idx, delta_temp)
        if comment:
            text_parts.append(f"🤖 _{md_escape(comment)}_\n")
        
        text_parts.append("\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\n")
        
        action_found = False

        # 3. Обработка растений
        for p in plants:
            plant_id = p.get("id", p.get("name", "unknown"))
            water_freq = p.get("waterFreq", 7)
            name = p.get("name", "Без имени")
            feed_short = p.get("feedShort", "")
            stage = str(p.get("stage", "")).strip().lower()

            # ПРОВЕРКА: Нужно ли поливать сегодня?
            days_passed = days_since_last_watering(plant_id, history)
            needs_water = days_passed >= water_freq
            
            # Если полив не требуется — пропускаем растение (не выводим)
            if not needs_water:
                continue

            action_found = True
            
            # ЛОГИКА УДОБРЕНИЙ: Проверяем стадию
            feed_msg = ""
            extra_tip = ""
            
            if stage in ("dormant", "покой"):
                # Если покой — удобрения игнорируем, даже если они есть в feedShort
                feed_msg = "Только вода \\(режим покоя\\)"
                extra_tip = "❄️ Не переливать\\!"
            elif stage in ("recover", "восстановление"):
                feed_msg = "Без подкормок \\(восстановление\\)"
            elif stage in ("bloom", "цветение"):
                feed_msg = md_escape(feed_short) if feed_short else "Подкормка для цветения"
                extra_tip = "🌸 Режим цветения"
            else:
                # Обычный режим (листва/рост) — выводим то, что в базе
                feed_msg = md_escape(feed_short) if feed_short else "Просто полив"

            # Формируем блок для растения
            line = f"📍 *{md_escape(name)}*\n"
            line += f"💧 {feed_msg}\n"
            if extra_tip:
                line += f"└ _{extra_tip}_\n"
            
            text_parts.append(line)
        
        # 4. Итог
        if not action_found:
            text_parts.append("✅ Сегодня полив никому не требуется\\. Отдыхаем\\!")
        
        full_text = "".join(text_parts)
        send_to_telegram(full_text)
        
        print("Задача завершена успешно")
    
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()

import os
import requests
import re
import ast
from datetime import datetime

def get_weather():
    api_key = os.getenv('OPENWEATHER_API_KEY')
    city = os.getenv('CITY_NAME', 'Moscow')
    if not api_key:
        return None
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url).json()
        if res.get("cod") != 200: return None
        return {
            "temp": res["main"]["temp"],
            "humidity": res["main"]["humidity"],
            "desc": res["weather"][0].get("description", "")
        }
    except:
        return None

def get_tasks():
    weather = get_weather()
    weather_header = ""
    if weather:
        weather_header = f"🌡 *Погода:* {weather['temp']}°C, {weather['desc']}\n💧 *Влажность:* {weather['humidity']}%\n"
        if weather['temp'] > 27:
            weather_header += "⚠️ *Жара! Проверь лимоны.*\n"
        weather_header += "───────────────\n\n"

    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        raw_data = re.sub(r'//.*', '', match.group(1))
        plants = ast.literal_eval(raw_data)

        now = datetime.now()
        d, m = now.day, now.month - 1
        msg = f"🌿 *План в саду на сегодня ({now.strftime('%d.%m')}):*\n\n{weather_header}"
        has_tasks = False

        for p in plants:
            tasks = []
            if p.get('waterFreq') == 1 or d % p.get('waterFreq', 99) == 0:
                tasks.append("💧 Полив")
                if m in p.get('feedMonths', []) and (p.get('waterFreq', 1) > 1 or d in [1, 15]):
                    tasks.append(f"🧪 {p.get('feedNote', 'Подкормка')}")
            
            if tasks:
                msg += f"🔹 *{p['name']}*:\n" + "\n".join([f"  — {t}" for t in tasks]) + "\n"
                if "warning" in p:
                    msg += f"  ❗ _{p['warning']}_\n"
                msg += "\n"
                has_tasks = True

        return msg if has_tasks else f"{weather_header}🌿 Сегодня в саду выходной!"
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    send_to_telegram(get_tasks())

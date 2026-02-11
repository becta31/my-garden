import os
import requests
import re
import ast
from datetime import datetime

# Твой погодный ключ и город (я подставил их сюда, чтобы точно заработало)
OWM_KEY = "cc6a00c91e119d29cf88e5425df2af0c"
CITY = "Moscow" # Если город другой, просто замени название

def get_weather():
    try:
        # Запрос погоды на русском языке
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OWM_KEY}&units=metric&lang=ru"
        res = requests.get(url).json()
        if res.get("cod") != 200:
            return None
        return {
            "temp": res["main"]["temp"],
            "humidity": res["main"]["humidity"],
            "desc": res["weather"][0]["description"]
        }
    except:
        return None

def get_tasks():
    weather = get_weather()
    weather_alert = ""
    
    if weather:
        temp = weather["temp"]
        hum = weather["humidity"]
        weather_alert = f"🌡 *Погода:* {temp}°C, {weather['desc']}. Влажность: {hum}%\n"
        if temp > 27:
            weather_alert += "⚠️ *Жара! Проверь лимоны и сеянцы — почва сохнет быстрее.*\n"
        if hum < 35:
            weather_alert += "⚠️ *Сухо! Не забудь опрыскать цитрусы и орхидеи.*\n"
        weather_alert += "───────────────\n\n"

    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
            
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        raw_data = re.sub(r'//.*', '', match.group(1))
        plants = ast.literal_eval(raw_data)

        now = datetime.now()
        d, m = now.day, now.month - 1
        
        msg = f"🌿 *План в саду на сегодня ({now.strftime('%d.%m')}):*\n\n"
        msg += weather_alert
        has_tasks = False

        for p in plants:
            tasks = []
            if p.get('waterFreq') == 1 or d % p.get('waterFreq', 99) == 0:
                tasks.append("💧 Полив")
                if m in p.get('feedMonths', []) and (p.get('waterFreq', 1) > 1 or d in [1, 15]):
                    tasks.append(f"🧪 {p.get('feedNote', 'Подкормка')}")
            
            if tasks:
                msg += f"🔹 *{p['name']}*:\n" + "\n".join([f"  — {t}" for t in tasks]) + "\n"
                # Вывод важных предупреждений (Warning) из твоей базы
                if "warning" in p:
                    msg += f"  ❗ _{p['warning']}_\n"
                msg += "\n"
                has_tasks = True

        return msg if has_tasks else f"{weather_alert}🌿 Сегодня в саду выходной! Все растения отдыхают."
    except Exception as e:
        return f"❌ Ошибка в данных: {str(e)}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("Ошибка: Проверь секреты TELEGRAM_TOKEN и TELEGRAM_CHAT_ID в GitHub!")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    send_to_telegram(get_tasks())

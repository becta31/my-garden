import os
import requests
import re
import ast
import time
import random
from datetime import datetime

# Настройки
LEIKA_VOLUME = 1.0 

def get_ai_advice(plants_info, weather):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key: return "Ключ не найден."
    
    # 1. Случайная задержка от 5 до 45 секунд (обход фильтров GitHub IP)
    time.sleep(random.randint(5, 45))
    
    # 2. Облегченный промпт (меньше токенов - меньше шансов на 429)
    prompt = f"Растения: {plants_info}. Погода: {weather}. Дай 1 короткий совет агронома (15 слов)."
    
    # 3. Переключаемся на 1.5-flash (у неё лимиты выше)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                return text.replace('*', '').replace('_', '')
            elif response.status_code == 429:
                # Если 429, ждем подольше
                time.sleep(20 * (attempt + 1))
                continue
            else:
                return f"Статус: {response.status_code}"
        except:
            time.sleep(10)
            
    return "Лимит запросов. Агроном ответит в следующий раз."

def get_weather():
    api_key = os.getenv('OPENWEATHER_API_KEY')
    city = os.getenv('CITY_NAME', 'Moscow')
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url).json()
        return {"temp": res["main"]["temp"], "humidity": res["main"]["humidity"], "desc": res["weather"][0]["description"]}
    except: return None

def get_tasks():
    weather = get_weather()
    w_info = f"{weather['temp']}C, {weather['desc']}" if weather else "норма"
    
    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        plants = ast.literal_eval(re.sub(r'//.*', '', match.group(1)))
        
        # Берем только имена растений для ИИ, чтобы сэкономить лимит
        names_only = ", ".join([p['name'] for p in plants])
        ai_advice = get_ai_advice(names_only, w_info)

        now = datetime.now()
        msg = f"🌿 *САДОВЫЙ ПЛАН ({now.strftime('%d.%m')})*\n\n"
        if weather:
            msg += f"🌡 *ПОГОДА:* {weather['temp']}°C | 💧 {weather['humidity']}%\n\n"
        
        msg += f"🤖 *СОВЕТ АГРОНОМА:* \n_{ai_advice}_\n\n"
        msg += "─" * 15 + "\n\n"

        has_tasks = False
        d, m = now.day, now.month - 1
        for p in plants:
            if p.get('waterFreq') == 1 or d % p.get('waterFreq', 99) == 0:
                msg += f"📍 *{p['name'].upper()}*\n  💧 ПОЛИВ\n"
                if m in p.get('feedMonths', []) and (p.get('waterFreq', 1) > 1 or d in [1, 15]):
                    msg += f"  🧪 {p.get('feedNote')}\n"
                if "warning" in p: msg += f"⚠️ _{p['warning']}_\n"
                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
                has_tasks = True
        return msg if has_tasks else "🌿 Сегодня отдыхаем!"
    except Exception as e: return f"Ошибка: {e}"

def send_to_telegram(text):
    token, chat_id = os.getenv('TELEGRAM_TOKEN'), os.getenv('TELEGRAM_CHAT_ID')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    send_to_telegram(get_tasks())

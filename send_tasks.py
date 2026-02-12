import os
import requests
import re
import ast
import json
from datetime import datetime

# Настройки
LEIKA_VOLUME = 1.0 

def get_ai_advice(plants_info, weather):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key: 
        return "ИИ-совет недоступен (ключ не найден в настройках GitHub)."
    
    # Промпт для агронома
    prompt = (
        f"Ты эксперт-растениевод. Погода: {weather}. Мои растения: {plants_info}. "
        f"В наличии: Осмокот (11-11-18), Bona Forte, Янтарная кислота. Лейка 1л. "
        f"Дай 1 короткий совет по уходу на сегодня (2 предложения). "
        f"Учти мороз и наличие сеянцев. Пиши кратко и профессионально."
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        # Тайм-аут увеличен до 30 секунд для надежности
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            # Извлекаем текст из структуры ответа Gemini
            try:
                advice = result['candidates'][0]['content']['parts'][0]['text']
                return advice.strip()
            except (KeyError, IndexWarning):
                return "Агроном задумался и не выдал ответ. Попробуй завтра."
        else:
            return f"Агроном занят (Ошибка {response.status_code})."
    except Exception as e:
        return f"Ошибка связи с ИИ: {str(e)[:50]}"

def get_weather():
    api_key = os.getenv('OPENWEATHER_API_KEY')
    city = os.getenv('CITY_NAME', 'Moscow')
    if not api_key: return None
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url).json()
        if res.get("cod") != 200: return None
        return {
            "temp": res["main"]["temp"], 
            "humidity": res["main"]["humidity"], 
            "desc": res["weather"][0].get("description", "")
        }
    except: return None

def get_tasks():
    weather = get_weather()
    weather_info = f"{weather['temp']}°C, {weather['desc']}" if weather else "неизвестна"
    
    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        if not match: return "❌ Ошибка: Данные в data.js не найдены."
        
        raw_data = re.sub(r'//.*', '', match.group(1))
        plants = ast.literal_eval(raw_data)
        
        # Получаем магию ИИ
        ai_advice = get_ai_advice(str(plants), weather_info)

        now = datetime.now()
        d, m = now.day, now.month - 1
        
        msg = f"🌿 *САДОВЫЙ ПЛАН ({now.strftime('%d.%m')})*\n\n"
        
        if weather:
            msg += f"🌡 *ПОГОДА:* {weather['temp']}°C ({weather['desc']})\n"
            msg += f"💧 *ВЛАЖНОСТЬ:* {weather['humidity']}%\n\n"
        
        msg += f"🤖 *СОВЕТ АГРОНОМА:* \n_{ai_advice}_\n"
        msg += "\n" + "─" * 15 + "\n\n"

        has_tasks = False
        for p in plants:
            tasks = []
            if p.get('waterFreq') == 1 or d % p.get('waterFreq', 99) == 0:
                tasks.append("  💧 *ПОЛИВ*")
                if m in p.get('feedMonths', []) and (p.get('waterFreq', 1) > 1 or d in [1, 15]):
                    tasks.append(f"  🧪 *РЕЦЕПТ:* {p.get('feedNote')}\n     _(на {LEIKA_VOLUME}л воды)_")
            
            if tasks:
                msg += f"📍 *{p['name'].upper()}*\n" + "\n".join(tasks) + "\n"
                if "warning" in p: 
                    msg += f"⚠️ _{p['warning']}_\n"
                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
                has_tasks = True

        return msg if has_tasks else f"🌿 На сегодня задач нет!"
    except Exception as e:
        return f"❌ Ошибка в скрипте: {str(e)}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    repo = os.getenv('GITHUB_REPOSITORY')
    
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Сделано!", "url": f"https://github.com/{repo}/actions"}
            ]]
        }
        payload = {
            "chat_id": chat_id, 
            "text": text, 
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }
        requests.post(url, json=payload)

if __name__ == "__main__":
    send_to_telegram(get_tasks())

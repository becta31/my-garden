import os
import requests
import re
import ast
import time
from datetime import datetime

def get_ai_advice(plants_info, weather):
    gemini_key = os.getenv('GEMINI_API_KEY', '').strip()
    hf_token = os.getenv('HF_API_TOKEN', '').strip()
    
    prompt = f"Растения: {plants_info}. Погода: {weather}. Ты агроном. Дай ОДИН короткий совет (15 слов) по уходу сегодня."

    # --- ТЕСТ GEMINI ---
    gemini_log = "G-None"
    if gemini_key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            if res.status_code == 200:
                text = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                return f"{text.replace('*', '')} (G)"
            else:
                gemini_log = f"G-Err:{res.status_code}"
        except:
            gemini_log = "G-Crash"

    # --- ТЕСТ HUGGING FACE (Llama-3-8B) ---
    hf_log = "H-None"
    if hf_token:
        # Переключились на более стабильную модель Llama-3
        url = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"
        headers = {"Authorization": f"Bearer {hf_token}"}
        # Формат промпта специально для Llama-3
        payload = {
            "inputs": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
            "parameters": {"max_new_tokens": 50, "temperature": 0.7}
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                raw_text = res.json()[0]['generated_text']
                # Извлекаем только ответ ассистента
                clean_text = raw_text.split("assistant")[-1].strip().replace('<|eot_id|>', '')
                return f"{clean_text.replace('*', '')} (H)"
            else:
                hf_log = f"H-Err:{res.status_code}"
        except:
            hf_log = "H-Crash"

    return f"Придерживайтесь графика. Логи: {gemini_log} | {hf_log}"

def get_weather():
    api_key = os.getenv('OPENWEATHER_API_KEY', '').strip()
    city = os.getenv('CITY_NAME', 'Moscow').strip()
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url, timeout=10).json()
        return {"temp": res["main"]["temp"], "desc": res["weather"][0]["description"]}
    except:
        return None

def get_tasks():
    weather = get_weather()
    w_info = f"{weather['temp']}C, {weather['desc']}" if weather else "комнатная"
    
    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        if not match: return "Ошибка БД: не найден plantsData"
        
        clean_js = re.sub(r'//.*', '', match.group(1))
        plants = ast.literal_eval(clean_js)
        
        # Передаем список имен для контекста ИИ
        names_only = ", ".join([p['name'] for p in plants[:5]])
        ai_advice = get_ai_advice(names_only, w_info)
        
        now = datetime.now()
        d = now.day
        
        msg = f"🌿 *САДОВЫЙ ПЛАН ({now.strftime('%d.%m')})*\n\n"
        if weather:
            msg += f"🌡 *ПОГОДА:* {weather['temp']}°C | {weather['desc'].capitalize()}\n"
        
        msg += f"🤖 *СОВЕТ:* _{ai_advice}_\n\n"
        msg += "─" * 15 + "\n\n"
        
        has_tasks = False
        for p in plants:
            if d % p.get('waterFreq', 99) == 0:
                msg += f"📍 *{p['name'].upper()}*\n  💧 ПОЛИВ\n"
                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
                has_tasks = True
        
        return msg if has_tasks else "🌿 Сегодня по плану отдых!"
    except Exception as e:
        return f"Ошибка при формировании задач: {e}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN', '').strip()
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat_id: return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Добавляем кнопку обратно для интерактивности
    reply_markup = {"inline_keyboard": [[{"text": "✅ Все полито!", "callback_data": "done"}]]}
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": reply_markup
    }
    requests.post(url, json=payload, timeout=10)

if __name__ == "__main__":
    send_to_telegram(get_tasks())

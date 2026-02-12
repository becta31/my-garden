import os
import requests
import re
import ast
from datetime import datetime

def get_ai_advice(plants_info, weather):
    gemini_key = os.getenv('GEMINI_API_KEY', '').strip()
    hf_token = os.getenv('HF_API_TOKEN', '').strip()
    
    prompt = f"Растения: {plants_info}. Погода: {weather}. Ты агроном. Дай короткий совет (15 слов)."

    # --- ТЕСТ GEMINI ---
    if gemini_key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text'].strip() + " (G)"
            else:
                gemini_log = f"G-Err:{res.status_code}" # Например 403 или 400
        except Exception as e:
            gemini_log = "G-Crash"
    else:
        gemini_log = "G-None"

    # --- ТЕСТ HUGGING FACE ---
    if hf_token:
        url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        headers = {"Authorization": f"Bearer {hf_token}"}
        try:
            res = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=15)
            if res.status_code == 200:
                return "Совет от HF (H)"
            else:
                hf_log = f"H-Err:{res.status_code}"
        except:
            hf_log = "H-Crash"
    else:
        hf_log = "H-None"

    return f"ИИ недоступен. Логи: {gemini_log} | {hf_log}"

def get_weather():
    api_key = os.getenv('OPENWEATHER_API_KEY', '').strip()
    city = os.getenv('CITY_NAME', 'Moscow').strip()
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url, timeout=10).json()
        return {"temp": res["main"]["temp"], "desc": res["weather"][0]["description"]}
    except: return None

def get_tasks():
    weather = get_weather()
    w_info = f"{weather['temp']}C, {weather['desc']}" if weather else "комнатная"
    
    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        clean_js = re.sub(r'//.*', '', match.group(1))
        plants = ast.literal_eval(clean_js)
        
        ai_advice = get_ai_advice("Коллекция растений", w_info)
        now = datetime.now()
        
        msg = f"🌿 *САДОВЫЙ ПЛАН ({now.strftime('%d.%m')})*\n\n"
        msg += f"🤖 *СОВЕТ:* _{ai_advice}_\n\n"
        msg += "─" * 15 + "\n"
        
        for p in plants:
            if now.day % p.get('waterFreq', 99) == 0:
                msg += f"📍 {p['name']} - ПОЛИВ\n"
        
        return msg
    except Exception as e:
        return f"Ошибка: {e}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN', '').strip()
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    send_to_telegram(get_tasks())

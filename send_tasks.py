import os
import requests
import re
import ast
import time
from datetime import datetime

def get_ai_advice(plants_info, weather):
    gemini_key = os.getenv('GEMINI_API_KEY', '').strip()
    hf_token = os.getenv('HF_API_TOKEN', '').strip()
    
    prompt = f"Растения: {plants_info}. Погода: {weather}. Ты агроном. Дай ОДИН короткий совет (10 слов) по уходу сегодня."

    # --- ВАРИАНТ 1: GEMINI (С использованием самой актуальной точки входа) ---
    g_log = "G-None"
    if gemini_key:
        # Исправленный URL: используем конкретную версию модели, которая точно существует
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={gemini_key}"
        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            if res.status_code == 200:
                data = res.json()
                text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                return f"{text.replace('*', '')} (G)"
            else:
                g_log = f"G-Err:{res.status_code}" # Если 404 - значит ключ не подходит к этой модели
        except: g_log = "G-Crash"

    # --- ВАРИАНТ 2: HUGGING FACE (Llama 3.2 - новейшая и стабильная) ---
    h_log = "H-None"
    if hf_token:
        # Обновленный URL на Llama 3.2
        url = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-1B-Instruct"
        headers = {"Authorization": f"Bearer {hf_token}"}
        payload = {
            "inputs": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
            "parameters": {"max_new_tokens": 50}
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                raw_text = res.json()[0]['generated_text']
                clean_text = raw_text.split("assistant")[-1].strip().replace('<|eot_id|>', '')
                return f"{clean_text[:100]} (H)"
            else:
                h_log = f"H-Err:{res.status_code}"
        except: h_log = "H-Crash"

    return f"Придерживайтесь графика. Логи: {g_log} | {h_log}"

def get_weather():
    api_key = os.getenv('OPENWEATHER_API_KEY', '').strip()
    city = os.getenv('CITY_NAME', 'Moscow').strip()
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url, timeout=10).json()
        return {"temp": res["main"]["temp"], "humidity": res["main"]["humidity"], "desc": res["weather"][0]["description"]}
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
        
        names_only = ", ".join([p['name'] for p in plants[:5]])
        ai_advice = get_ai_advice(names_only, w_info)
        
        now = datetime.now()
        msg = f"🌿 *САДОВЫЙ ПЛАН ({now.strftime('%d.%m')})*\n\n"
        if weather:
            msg += f"🌡 *ПОГОДА:* {weather['temp']}°C | 💧 {weather['humidity']}% | {weather['desc'].capitalize()}\n"
        msg += f"🤖 *СОВЕТ АГРОНОМА:* \n_{ai_advice}_\n\n"
        msg += "─" * 15 + "\n\n"
        
        d, m = now.day, now.month - 1
        for p in plants:
            if d % p.get('waterFreq', 99) == 0:
                msg += f"📍 *{p['name'].upper()}*\n  💧 ПОЛИВ\n"
                if m in p.get('feedMonths', []):
                    if p.get('waterFreq', 1) > 1 or d in [1, 15]:
                        msg += f"  🧪 {p.get('feedNote')}\n"
                if "warning" in p: msg += f"⚠️ _{p['warning']}_\n"
                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        return msg
    except Exception as e: return f"Ошибка: {e}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN', '').strip()
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown", 
               "reply_markup": {"inline_keyboard": [[{"text": "✅ Все полито!", "callback_data": "done"}]]}}
    requests.post(url, json=payload, timeout=10)

if __name__ == "__main__":
    send_to_telegram(get_tasks())

import os
import requests
import re
import ast
from datetime import datetime
from google import genai
from openai import OpenAI

def get_ai_advice(plants_info, weather):
    gemini_key = os.getenv('GEMINI_API_KEY', '').strip()
    hf_token = os.getenv('HF_API_TOKEN', '').strip()
    
    prompt = f"Ты агроном. Растения: {plants_info}. Погода: {weather}. Дай ОДИН совет (10 слов)."

    # --- ПОПЫТКА 1: GEMINI (через новый SDK) ---
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-1.5-flash", 
                contents=prompt
            )
            if response.text:
                return f"{response.text.strip()} (G)"
        except Exception as e:
            print(f"Gemini error: {e}")

    # --- ПОПЫТКА 2: HUGGING FACE (через Router) ---
    if hf_token:
        try:
            client = OpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=hf_token,
            )
            completion = client.chat.completions.create(
                model="Qwen/Qwen2.5-7B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50
            )
            return f"{completion.choices[0].message.content.strip()} (H)"
        except Exception as e:
            print(f"HF error: {e}")

    return "Следите за влажностью почвы и светом. (Default)"

def get_weather():
    api_key = os.getenv('OPENWEATHER_API_KEY', '').strip()
    city = os.getenv('CITY_NAME', 'Moscow').strip()
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url, timeout=10).json()
        return {
            "temp": res["main"]["temp"], 
            "hum": res["main"]["humidity"], 
            "desc": res["weather"][0]["description"]
        }
    except: return None

def get_tasks():
    weather = get_weather()
    w_info = f"{weather['temp']}C, {weather['desc']}" if weather else "комнатная"
    
    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        plants = ast.literal_eval(re.sub(r'//.*', '', match.group(1)))
        
        # Берем названия первых 3 растений для контекста
        names = ", ".join([p['name'] for p in plants[:3]])
        ai_advice = get_ai_advice(names, w_info)
        
        now = datetime.now()
        msg = f"🌿 *САДОВЫЙ ПЛАН ({now.strftime('%d.%m')})*\n\n"
        if weather:
            msg += f"🌡 *ПОГОДА:* {weather['temp']}°C | 💧 {weather['hum']}% | {weather['desc'].capitalize()}\n"
        msg += f"🤖 *СОВЕТ:* _{ai_advice}_\n\n"
        msg += "─" * 15 + "\n\n"
        
        d = now.day
        for p in plants:
            if d % p.get('waterFreq', 99) == 0:
                msg += f"📍 *{p['name'].upper()}* - ПОЛИВ\n"
                if "warning" in p: msg += f"⚠️ _{p['warning']}_\n"
                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        return msg
    except Exception as e: return f"Ошибка: {e}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN', '').strip()
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, "text": text, "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": [[{"text": "✅ Все полито!", "callback_data": "done"}]]}
    }
    requests.post(url, json=payload, timeout=10)

if __name__ == "__main__":
    send_to_telegram(get_tasks())

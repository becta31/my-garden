import os
import requests
import re
import ast
from datetime import datetime
from openai import OpenAI # Не забудь добавить в workflow!

def get_ai_advice(plants_info, weather):
    hf_token = os.getenv('HF_API_TOKEN', '').strip()
    if not hf_token:
        return "Придерживайтесь графика (Нет токена)"

    try:
        # Используем новый Router от Hugging Face
        client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=hf_token,
        )

        prompt = f"Ты агроном. Растения: {plants_info}. Погода: {weather}. Дай ОДИН короткий совет (10 слов)."

        completion = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct", # Можно менять на Llama-3.1-8B-Instruct
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50
        )
        
        advice = completion.choices[0].message.content.strip()
        return f"{advice} (AI)"
    except Exception as e:
        return f"Придерживайтесь графика. (Ошибка ИИ: {str(e)[:20]})"

def get_weather():
    api_key = os.getenv('OPENWEATHER_API_KEY', '').strip()
    city = os.getenv('CITY_NAME', 'Moscow').strip()
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url, timeout=10).json()
        return {"temp": res["main"]["temp"], "hum": res["main"]["humidity"], "desc": res["weather"][0]["description"]}
    except: return None

def get_tasks():
    weather = get_weather()
    w_info = f"{weather['temp']}C, {weather['desc']}" if weather else "комнатная"
    
    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        plants = ast.literal_eval(re.sub(r'//.*', '', match.group(1)))
        
        names_only = ", ".join([p['name'] for p in plants[:3]])
        ai_advice = get_ai_advice(names_only, w_info)

        now = datetime.now()
        msg = f"🌿 *САДОВЫЙ ПЛАН ({now.strftime('%d.%m')})*\n\n"
        if weather:
            msg += f"🌡 *ПОГОДА:* {weather['temp']}°C | 💧 {weather['hum']}% | {weather['desc'].capitalize()}\n"
        
        msg += f"🤖 *СОВЕТ АГРОНОМА:* \n_{ai_advice}_\n\n"
        msg += "─" * 15 + "\n\n"

        d = now.day
        has_tasks = False
        for p in plants:
            if d % p.get('waterFreq', 99) == 0:
                msg += f"📍 *{p['name'].upper()}* - ПОЛИВ\n"
                has_tasks = True
        
        return msg if has_tasks else "🌿 Сегодня отдых!"
    except Exception as e:
        return f"Ошибка формирования: {e}"

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

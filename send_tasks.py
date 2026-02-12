import os
import requests
import re
import ast
import time
import random
from datetime import datetime

def get_ai_advice(plants_info, weather):
    gemini_key = os.getenv('GEMINI_API_KEY')
    hf_token = os.getenv('HF_API_TOKEN')
    
    prompt = f"Растения: {plants_info}. Погода: {weather}. Ты агроном. Дай ОДИН короткий совет (15 слов) по уходу сегодня."

    # --- ВАРИАНТ 1: GEMINI (Основной) ---
    if gemini_key:
        print("Запрос к Gemini...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        try:
            # Небольшая пауза для обхода лимитов
            time.sleep(random.randint(2, 5))
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            if res.status_code == 200:
                text = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                return text.replace('*', '').replace('_', '')
        except Exception as e:
            print(f"Gemini ошибка: {e}")

    # --- ВАРИАНТ 2: HUGGING FACE (Запасной) ---
    if hf_token:
        print("Gemini не ответил. Запрос к Hugging Face (Mistral)...")
        url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        headers = {"Authorization": f"Bearer {hf_token}"}
        payload = {
            "inputs": f"<s>[INST] {prompt} [/INST] ",
            "parameters": {"max_new_tokens": 50, "temperature": 0.7}
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                raw_text = res.json()[0]['generated_text']
                # Очищаем ответ от промпта (Mistral иногда возвращает всё вместе)
                clean_text = raw_text.split("[/INST]")[-1].strip()
                return clean_text.replace('*', '').replace('_', '')
        except Exception as e:
            print(f"HF ошибка: {e}")

    return "Агроном на связи: сегодня придерживайтесь стандартного графика полива."

def get_weather():
    api_key = os.getenv('OPENWEATHER_API_KEY')
    city = os.getenv('CITY_NAME', 'Moscow')
    if not api_key: return None
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url, timeout=10).json()
        return {"temp": res["main"]["temp"], "humidity": res["main"]["humidity"], "desc": res["weather"][0].get("description", "ясно")}
    except: return None

def get_tasks():
    weather = get_weather()
    w_info = f"{weather['temp']}C, {weather['desc']}" if weather else "комнатная"
    
    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        if not match: return "Ошибка: база данных не найдена."
        
        # Очистка от комментариев и парсинг
        clean_js = re.sub(r'//.*', '', match.group(1))
        plants = ast.literal_eval(clean_js)
        
        # Получаем ИИ-совет
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
        
        return msg if has_tasks else "🌿 Сегодня по плану отдых и созерцание!"
    except Exception as e:
        return f"Ошибка при формировании задач: {e}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)

if __name__ == "__main__":
    content = get_tasks()
    send_to_telegram(content)

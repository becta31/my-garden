import os
import requests
import re
import ast
import time
from datetime import datetime

def get_ai_advice(plants_info, weather):
    # .strip() страхует от случайных пробелов при вставке секретов в GitHub
    gemini_key = os.getenv('GEMINI_API_KEY', '').strip()
    hf_token = os.getenv('HF_API_TOKEN', '').strip()
    
    prompt = f"Растения: {plants_info}. Погода: {weather}. Ты агроном. Дай ОДИН очень короткий совет (10-15 слов) по уходу сегодня."

    # --- ВАРИАНТ 1: GEMINI (Стабильная модель 1.5 Flash) ---
    g_log = "G-None"
    if gemini_key:
        # Прямой URL к стабильной версии модели
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            if res.status_code == 200:
                data = res.json()
                text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                # Убираем лишние символы форматирования ИИ
                clean_text = text.replace('*', '').replace('_', '').replace('#', '')
                return f"{clean_text} (G)"
            else:
                g_log = f"G-Err:{res.status_code}"
        except Exception as e:
            g_log = "G-Crash"

    # --- ВАРИАНТ 2: HUGGING FACE (Llama 3.1 — замена удаленному Mistral) ---
    h_log = "H-None"
    if hf_token:
        # Используем одну из самых стабильных бесплатных моделей на HF
        url = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.1-8B-Instruct"
        headers = {"Authorization": f"Bearer {hf_token}"}
        payload = {
            "inputs": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
            "parameters": {"max_new_tokens": 100, "temperature": 0.7}
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                raw_text = res.json()[0]['generated_text']
                # Извлекаем только то, что ответил ассистент после промпта
                clean_text = raw_text.split("assistant")[-1].strip().replace('<|eot_id|>', '')
                return f"{clean_text[:150].replace('*', '')} (H)"
            else:
                h_log = f"H-Err:{res.status_code}"
        except Exception as e:
            h_log = "H-Crash"

    # Если оба ИИ не ответили, выводим коды ошибок для диагностики
    return f"Придерживайтесь стандартного графика. Логи: {g_log} | {h_log}"

def get_weather():
    api_key = os.getenv('OPENWEATHER_API_KEY', '').strip()
    city = os.getenv('CITY_NAME', 'Moscow').strip()
    if not api_key: return None
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url, timeout=10).json()
        return {
            "temp": res["main"]["temp"], 
            "humidity": res["main"]["humidity"],
            "desc": res["weather"][0]["description"]
        }
    except:
        return None

def get_tasks():
    weather = get_weather()
    w_info = f"{weather['temp']}C, {weather['desc']}" if weather else "комнатная"
    
    try:
        # Читаем базу данных из data.js
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Находим массив данных
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        if not match: return "Ошибка: база данных в data.js не найдена."
        
        # Очищаем JS от комментариев для парсинга в Python
        clean_js = re.sub(r'//.*', '', match.group(1))
        plants = ast.literal_eval(clean_js)
        
        # Готовим контекст для ИИ (берем первые 5 растений)
        names_only = ", ".join([p['name'] for p in plants[:5]])
        ai_advice = get_ai_advice(names_only, w_info)
        
        now = datetime.now()
        d, m = now.day, now.month - 1 # m - индекс месяца (0-11)
        
        msg = f"🌿 *САДОВЫЙ ПЛАН ({now.strftime('%d.%m')})*\n\n"
        if weather:
            msg += f"🌡 *ПОГОДА:* {weather['temp']}°C | 💧 {weather['humidity']}% | {weather['desc'].capitalize()}\n"
        
        msg += f"🤖 *СОВЕТ АГРОНОМА:* \n_{ai_advice}_\n\n"
        msg += "─" * 15 + "\n\n"
        
        has_tasks = False
        for p in plants:
            # Проверка частоты полива
            if d % p.get('waterFreq', 99) == 0:
                msg += f"📍 *{p['name'].upper()}*\n  💧 ПОЛИВ\n"
                
                # Проверка подкормки (если текущий месяц в списке feedMonths)
                if m in p.get('feedMonths', []):
                    # Кормим либо если полив редкий, либо по числам (1 и 15) для ежедневных
                    if p.get('waterFreq', 1) > 1 or d in [1, 15]:
                        msg += f"  🧪 {p.get('feedNote')}\n"
                
                if "warning" in p:
                    msg += f"⚠️ _{p['warning']}_\n"
                
                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
                has_tasks = True
        
        return msg if has_tasks else "🌿 Сегодня по плану отдых и созерцание!"
        
    except Exception as e:
        return f"Ошибка при формировании задач: {e}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN', '').strip()
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat_id: return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Кнопка подтверждения
    reply_markup = {
        "inline_keyboard": [[
            {"text": "✅ Все полито!", "callback_data": "done"}
        ]]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": reply_markup
    }
    
    try:
        requests.post(url, json=payload, timeout=12)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

if __name__ == "__main__":
    content = get_tasks()
    send_to_telegram(content)

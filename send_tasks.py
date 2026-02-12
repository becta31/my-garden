import os
import requests
import re
import ast
from datetime import datetime
from openai import OpenAI

def get_ai_advice(plants_info, weather):
    # Берем токен из env, который прописан в YAML
    hf_token = os.getenv('HF_API_TOKEN', '').strip()
    
    if not hf_token:
        return "Придерживайтесь графика (Токен не найден)"

    try:
        # Используем OpenAI-совместимый клиент для Hugging Face Router
        client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=hf_token,
        )

        prompt = f"Ты агроном. Растения: {plants_info}. Погода: {weather}. Дай ОДИН очень короткий совет (10 слов)."

        completion = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.7
        )
        
        advice = completion.choices[0].message.content.strip()
        # Убираем кавычки, если ИИ их добавил
        return advice.replace('"', '') + " (H)"
        
    except Exception as e:
        # Если ИИ упал, выводим краткую ошибку для отладки
        return f"Поливайте по графику. (Ошибка: {str(e)[:15]})"

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
        # Очистка от комментариев // и преобразование в список Python
        plants = ast.literal_eval(re.sub(r'//.*', '', match.group(1)))
        
        # Передаем список растений для контекста (первые 3-4 названия)
        names_context = ", ".join([p['name'] for p in plants[:4]])
        ai_advice = get_ai_advice(names_context, w_info)

        now = datetime.now()
        msg = f"🌿 *САДОВЫЙ ПЛАН ({now.strftime('%d.%m')})*\n\n"
        
        if weather:
            msg += f"🌡 *ПОГОДА:* {weather['temp']}°C | 💧 {weather['hum']}% | {weather['desc'].capitalize()}\n"
        
        msg += f"🤖 *СОВЕТ АГРОНОМА:* \n_{ai_advice}_\n\n"
        msg += "─" * 15 + "\n\n"

        d, m = now.day, now.month - 1
        has_tasks = False
        
        for p in plants:
            # Проверка дня полива
            if d % p.get('waterFreq', 99) == 0:
                msg += f"📍 *{p['name'].upper()}*\n  💧 ПОЛИВ\n"
                
                # Проверка подкормки
                if m in p.get('feedMonths', []):
                    if p.get('waterFreq', 1) > 1 or d in [1, 15]:
                        msg += f"  🧪 {p.get('feedNote')}\n"
                
                if "warning" in p:
                    msg += f"⚠️ _{p['warning']}_\n"
                
                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
                has_tasks = True
        
        return msg if has_tasks else "🌿 Сегодня только отдых и осмотр!"
        
    except Exception as e:
        return f"Ошибка парсинга data.js: {e}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN', '').strip()
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat_id: return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": [[{"text": "✅ Все полито!", "callback_data": "done"}]]}
    }
    requests.post(url, json=payload, timeout=12)

if __name__ == "__main__":
    send_to_telegram(get_tasks())

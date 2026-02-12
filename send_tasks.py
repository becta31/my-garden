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
    
    # Получаем текущий месяц на русском
    months = ["январе", "феврале", "марте", "апреле", "мае", "июне", 
              "июле", "августе", "сентябре", "октябре", "ноябре", "декабре"]
    now = datetime.now()
    month_name = months[now.month - 1]

    # МАКСИМАЛЬНЫЙ ПРОМПТ: Указываем условия квартиры и отопления
    prompt = (
        f"Ты эксперт-агроном. Сейчас середина февраля. Растения стоят В КВАРТИРЕ, "
        f"где сейчас очень СУХОЙ ВОЗДУХ из-за отопления. На улице: {weather}. "
        f"Список твоих подопечных: {plants_info}. "
        f"Дай один дельный совет по уходу (до 12 слов), учитывая домашнее тепло."
    )

    # --- ПОПЫТКА 1: GEMINI 1.5 FLASH (Самый умный) ---
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            # Используем модель 1.5-flash через официальный SDK
            response = client.models.generate_content(
                model="gemini-1.5-flash", 
                contents=prompt
            )
            if response.text:
                return f"{response.text.strip().replace('*', '')} (G)"
        except Exception as e:
            print(f"Gemini error: {e}")

    # --- ПОПЫТКА 2: Llama 3.1 8B через Router (Надежный запасной) ---
    if hf_token:
        try:
            client = OpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=hf_token,
            )
            completion = client.chat.completions.create(
                model="meta-llama/Llama-3.1-8B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60,
                temperature=0.6 # Делаем советы более строгими и по делу
            )
            advice = completion.choices[0].message.content.strip()
            return f"{advice.replace('*', '')} (H)"
        except Exception as e:
            print(f"HF error: {e}")

    return "Опрыскивайте листья и следите за влажностью почвы из-за батарей. (Default)"

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
    except:
        return None

def get_tasks():
    weather = get_weather()
    w_info = f"{weather['temp']}°C, {weather['desc']}" if weather else "комнатная"
    
    try:
        # Читаем базу из data.js
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Извлекаем массив растений
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        if not match:
            return "Ошибка: не найден plantsData в data.js"
            
        # Убираем JS-комментарии для корректного парсинга
        clean_js = re.sub(r'//.*', '', match.group(1))
        plants = ast.literal_eval(clean_js)
        
        # Передаем ИИ имена ВСЕХ растений для точности
        all_names = ", ".join([p['name'] for p in plants])
        ai_advice = get_ai_advice(all_names, w_info)
        
        now = datetime.now()
        day, month_idx = now.day, now.month - 1
        
        msg = f"🌿 *САДОВЫЙ ПЛАН ({now.strftime('%d.%m')})*\n\n"
        if weather:
            msg += f"🌡 *ПОГОДА:* {weather['temp']}°C | 💧 {weather['hum']}% | {weather['desc'].capitalize()}\n"
        
        msg += f"🤖 *СОВЕТ АГРОНОМА:* \n_{ai_advice}_\n\n"
        msg += "─" * 15 + "\n\n"
        
        has_tasks = False
        for p in plants:
            # Проверка частоты полива
            if day % p.get('waterFreq', 99) == 0:
                msg += f"📍 *{p['name'].upper()}*\n  💧 ПОЛИВ\n"
                
                # Проверка подкормки (если текущий месяц в списке feedMonths)
                if month_idx in p.get('feedMonths', []):
                    # Кормим либо по частоте полива, либо каждое 1 и 15 число
                    if p.get('waterFreq', 1) > 1 or day in [1, 15]:
                        msg += f"  🧪 {p.get('feedNote')}\n"
                
                if "warning" in p:
                    msg += f"⚠️ _{p['warning']}_\n"
                
                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
                has_tasks = True
        
        return msg if has_tasks else "🌿 Сегодня по плану только отдых и осмотр!"
        
    except Exception as e:
        return f"Ошибка при формировании задач: {e}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN', '').strip()
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat_id:
        print("Telegram credentials missing!")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Добавляем кнопку подтверждения
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "✅ Все полито!", "callback_data": "done"}
            ]]
        }
    }
    
    try:
        requests.post(url, json=payload, timeout=12)
    except Exception as e:
        print(f"Telegram send error: {e}")

if __name__ == "__main__":
    content = get_tasks()
    send_to_telegram(content)

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
    
    prompt = (
        f"Ты эксперт-агроном. Февраль, растения в квартире, сухой воздух. "
        f"На улице: {weather}. Растения: {plants_info}. "
        f"Дай один дельный совет по уходу (до 10 слов)."
    )

    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            if response.text: return f"{response.text.strip().replace('*', '')} (G)"
        except: pass

    if hf_token:
        try:
            client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=hf_token)
            completion = client.chat.completions.create(
                model="meta-llama/Llama-3.1-8B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50, temperature=0.6
            )
            return f"{completion.choices[0].message.content.strip().replace('*', '')} (H)"
        except: pass

    return "Опрыскивайте листья и следите за влажностью почвы. (D)"

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
    w_info = f"{weather['temp']}°C, {weather['desc']}" if weather else "комнатная"
    
    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        clean_js = re.sub(r'//.*', '', match.group(1))
        plants = ast.literal_eval(clean_js)
        
        all_names = ", ".join([p['name'] for p in plants])
        ai_advice = get_ai_advice(all_names, w_info)
        
        now = datetime.now()
        day, month_idx = now.day, now.month - 1
        
        # --- ФОРМАТИРОВАНИЕ СООБЩЕНИЯ ---
        msg = f"🌿 *ПЛАН САДА — {now.strftime('%d.%m')}*\n"
        if weather:
            msg += f"🌡 {weather['temp']}°C | 💧 {weather['hum']}% | {weather['desc'].capitalize()}\n"
        
        msg += f"\n🤖 _{ai_advice}_\n"
        msg += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        
        tasks_count = 0
        for p in plants:
            if day % p.get('waterFreq', 99) == 0:
                tasks_count += 1
                msg += f"📍 *{p['name'].upper()}*\n"
                
                # Базовая задача
                task_line = "💧 Полив"
                
                # Добавляем подкормку, если месяц совпадает
                if month_idx in p.get('feedMonths', []):
                    # Кормим в дни полива (или 1 и 15 числа)
                    if p.get('waterFreq', 1) > 1 or day in [1, 15]:
                        # Просто берем описание из базы (там уже есть дозировка)
                        feed_info = p.get('feedNote', 'Удобрение')
                        task_line += f" + 🧪 *{feed_info}*"
                
                msg += f"{task_line}\n"
                
                # Компактное предупреждение
                if "warning" in p:
                    short_warn = p['warning'].replace('Мороз за окном! ', '❄️ ')
                    msg += f"└ _{short_warn}_\n"
                
                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        
        if tasks_count > 0:
            msg += f"\n✅ *Всего к поливу: {tasks_count}*"
            return msg
        else:
            return "🌿 *Сегодня по расписанию только отдых!*"
        
    except Exception as e:
        return f"Ошибка парсинга базы: {e}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN', '').strip()
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat_id: return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, "text": text, "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": [[{"text": "✅ Выполнено", "callback_data": "done"}]]}
    }
    requests.post(url, json=payload, timeout=12)

if __name__ == "__main__":
    send_to_telegram(get_tasks())

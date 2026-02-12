import os
import requests
import re
import ast
from datetime import datetime
from openai import OpenAI

def get_ai_advice(plants_info, weather_data):
    hf_token = os.getenv('HF_API_TOKEN', '').strip()
    if not hf_token:
        return "⚠️ Добавьте HF_API_TOKEN в секреты GitHub."

    client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=hf_token)
    
    # Извлекаем данные погоды
    temp = weather_data.get('temp', 22)
    hum = weather_data.get('hum', 40)
    desc = weather_data.get('desc', 'комнатная')

    # ШАГ 1: Запрос к Агроному (Llama 3.1)
    # Указываем контекст про "молодняк"
    prompt_agronomist = (
        f"Ты агроном. В комнате {temp}C, влажность {hum}%. Растения: {plants_info}. "
        f"Учти, что в составе есть молодняк (сеянцы). Дай ОДИН короткий совет (до 10 слов)."
    )

    advice_llama = "Следите за влажностью почвы." # Заглушка
    try:
        res1 = client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[{"role": "user", "content": prompt_agronomist}],
            max_tokens=50,
            timeout=10
        )
        advice_llama = res1.choices[0].message.content.strip().replace('*', '')
    except Exception as e:
        print(f"Ошибка Llama: {e}")

    # ШАГ 2: Запрос к Профессору (Qwen 72B) - Контроль качества
    prompt_professor = (
        f"Контекст: {plants_info}, климат {temp}C/{hum}%. "
        f"Твой коллега-агроном дал совет: '{advice_llama}'. "
        f"Как эксперт, подтверди его или исправь, если он опасен для молодых растений. "
        f"Будь краток, максимум 15 слов."
    )

    try:
        res2 = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[{"role": "user", "content": prompt_professor}],
            max_tokens=70,
            timeout=15 # Даем больше времени тяжелой модели
        )
        advice_qwen = res2.choices[0].message.content.strip().replace('*', '')
        # Возвращаем диалог двух моделей
        return f"👨‍🌾: {advice_llama}\n🎓: {advice_qwen}"
    except Exception as e:
        print(f"Ошибка Qwen: {e}")
        # Если Qwen не ответила, возвращаем хотя бы совет Llama
        return f"👨‍🌾: {advice_llama} (Профессор занят)"

def get_weather():
    api_key = os.getenv('OPENWEATHER_API_KEY', '').strip()
    city = os.getenv('CITY_NAME', 'Moscow').strip()
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url, timeout=10).json()
        return {
            "temp": round(res["main"]["temp"]), 
            "hum": res["main"]["humidity"], 
            "desc": res["weather"][0]["description"]
        }
    except:
        return {"temp": 22, "hum": 40, "desc": "нет данных"}

def get_tasks():
    weather = get_weather()
    
    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        clean_js = re.sub(r'//.*', '', match.group(1))
        plants = ast.literal_eval(clean_js)
        
        all_names = ", ".join([p['name'] for p in plants])
        ai_advice = get_ai_advice(all_names, weather)
        
        now = datetime.now()
        day, month_idx = now.day, now.month - 1
        
        # Формирование сообщения
        msg = f"🌿 *ПЛАН САДА — {now.strftime('%d.%m')}*\n"
        msg += f"🌡 {weather['temp']}°C | 💧 {weather['hum']}% | {weather['desc'].capitalize()}\n\n"
        msg += f"🤖 *СОВЕТ ЭКСПЕРТОВ:*\n_{ai_advice}_\n"
        msg += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        
        tasks_count = 0
        for p in plants:
            if day % p.get('waterFreq', 99) == 0:
                tasks_count += 1
                msg += f"📍 *{p['name'].upper()}*\n"
                
                task_line = "💧 Полив"
                if month_idx in p.get('feedMonths', []):
                    if p.get('waterFreq', 1) > 1 or day in [1, 15]:
                        feed_info = p.get('feedNote', 'Удобрение')
                        task_line += f" + 🧪 *{feed_info}*"
                
                msg += f"{task_line}\n"
                
                if "warning" in p:
                    short_warn = p['warning'].replace('Мороз за окном! ', '❄️ ')
                    msg += f"└ _{short_warn}_\n"
                
                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        
        if tasks_count > 0:
            msg += f"\n✅ *Всего к поливу: {tasks_count}*"
        else:
            msg += "\n🌿 *Сегодня по расписанию только отдых!*"
        
        return msg
        
    except Exception as e:
        return f"Ошибка парсинга базы: {e}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN', '').strip()
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat_id: return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, "text": text, "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": [[{"text": "✅ Сделано!", "callback_data": "done"}]]}
    }
    try:
        requests.post(url, json=payload, timeout=12)
    except: pass

if __name__ == "__main__":
    send_to_telegram(get_tasks())

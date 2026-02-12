import os
import requests
import re
import ast
from datetime import datetime

# --- ТВОИ НАСТРОЙКИ ---
LEIKA_VOLUME = 1.0  # Объем твоей лейки в литрах

def get_weather():
    api_key = os.getenv('OPENWEATHER_API_KEY')
    city = os.getenv('CITY_NAME', 'Moscow')
    
    if not api_key:
        return None
        
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        res = requests.get(url).json()
        
        if res.get("cod") != 200:
            return None
            
        return {
            "temp": res["main"]["temp"],
            "humidity": res["main"]["humidity"],
            "desc": res["weather"][0].get("description", "")
        }
    except:
        return None

def get_tasks():
    weather = get_weather()
    weather_header = ""
    
    if weather:
        weather_header = (
            f"🌤 *ПОГОДА ЗА ОКНОМ*\n"
            f"🌡 Температура: {weather['temp']}°C ({weather['desc']})\n"
            f"💧 Влажность: {weather['humidity']}%\n"
        )
        
        # Блок оперативных советов на основе погоды
        advice = []
        if weather['temp'] < 0:
            advice.append("❄️ *МОРОЗ:* Полив только тёплой водой (~30°C)!")
        if weather['humidity'] > 70 and weather['temp'] < 0:
            advice.append("💨 *СУХОЙ ВОЗДУХ:* Дома жарят батареи. Цитрусам нужно опрыскивание!")
        
        if advice:
            weather_header += "\n" + "\n".join(advice)
            
        weather_header += "\n" + "─" * 15 + "\n\n"

    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем массив plantsData в JS файле
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        if not match:
            return "❌ Ошибка: Не удалось прочитать данные из data.js"
            
        raw_data = re.sub(r'//.*', '', match.group(1))
        plants = ast.literal_eval(raw_data)

        now = datetime.now()
        d, m = now.day, now.month - 1
        msg = f"🌿 *САДОВЫЙ ПЛАН ({now.strftime('%d.%m')})*\n\n{weather_header}"
        has_tasks = False

        for p in plants:
            tasks = []
            # Проверка частоты полива (кратность дням)
            if p.get('waterFreq') == 1 or d % p.get('waterFreq', 99) == 0:
                tasks.append("  💧 *ПОЛИВ*")
                
                # Проверка подкормки (если текущий месяц в списке и день 1, 15 или редкий полив)
                if m in p.get('feedMonths', []) and (p.get('waterFreq', 1) > 1 or d in [1, 15]):
                    feed_info = p.get('feedNote', 'Подкормка')
                    tasks.append(f"  🧪 *РЕЦЕПТ:* {feed_info}\n     _(на {LEIKA_VOLUME}л воды)_")
            
            if tasks:
                msg += f"📍 *{p['name'].upper()}*\n" + "\n".join(tasks) + "\n"
                if "warning" in p:
                    msg += f"⚠️ _{p['warning']}_\n"
                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
                has_tasks = True

        return msg if has_tasks else f"{weather_header}🌿 На сегодня задач нет. Отдыхаем!"
    except Exception as e:
        return f"❌ Ошибка в расчетах: {str(e)}"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    repo = os.getenv('GITHUB_REPOSITORY')
    
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        # Кнопка со ссылкой на лог выполнения в GitHub
        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Сделано! (В лог)", "url": f"https://github.com/{repo}/actions"}
            ]]
        }
        
        payload = {
            "chat_id": chat_id, 
            "text": text, 
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Ошибка отправки: {e}")

if __name__ == "__main__":
    send_to_telegram(get_tasks())

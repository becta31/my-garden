import os
import requests
import re
import ast
from datetime import datetime

def get_tasks():
    try:
        # Читаем наш файл с растениями
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Ищем массив данных внутри переменной plantsData
        match = re.search(r'const\s+plantsData\s*=\s*(\[.*\]);', content, re.DOTALL)
        if not match:
            return "❌ Ошибка: Не удалось найти данные в data.js"
        
        # Превращаем текст в список Python (метод ast прощает мелкие ошибки формата)
        raw_data = match.group(1)
        # Удаляем лишние пробелы и комментарии для чистоты
        raw_data = re.sub(r'//.*', '', raw_data)
        plants = ast.literal_eval(raw_data)

        now = datetime.now()
        d, m = now.day, now.month - 1
        
        msg = "🌿 *План в саду на сегодня:*\n\n"
        has_tasks = False

        for p in plants:
            tasks = []
            # Проверка частоты полива
            if p.get('waterFreq') == 1 or d % p.get('waterFreq', 99) == 0:
                tasks.append("💧 Полив")
                
                # Проверка подкормки (если месяц совпадает и сегодня 1 или 15 число, либо редкий полив)
                if m in p.get('feedMonths', []) and (p.get('waterFreq', 1) > 1 or d in [1, 15]):
                    tasks.append(f"🧪 {p.get('feedNote', 'Подкормка')}")
            
            if tasks:
                msg += f"🔹 *{p['name']}*:\n" + "\n".join([f"  — {t}" for t in tasks]) + "\n\n"
                has_tasks = True

        return msg if has_tasks else "🌿 Сегодня в саду выходной! Все растения в порядке."
    except Exception as e:
        return f"❌ Ошибка внутри скрипта: {str(e)}"

def send_to_telegram(text):
    # Берем ключи из секретов GitHub
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ Ошибка: Проверь секреты TELEGRAM_TOKEN и TELEGRAM_CHAT_ID!")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text, 
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ Ошибка Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Не удалось отправить сообщение: {e}")

if __name__ == "__main__":
    tasks_text = get_tasks()
    send_to_telegram(tasks_text)

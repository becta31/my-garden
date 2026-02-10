import os
import requests
import json
import re
from datetime import datetime

def get_tasks():
    # Читаем data.js (убираем JS-обертку, оставляя чистый JSON)
    with open('data.js', 'r', encoding='utf-8') as f:
        content = f.read()
        # Извлекаем массив из переменной plantsData
        json_str = re.search(r'const plantsData = (\[.*\]);', content, re.DOTALL).group(1)
        # Убираем возможные комментарии, чтобы JSON распарсился
        json_str = re.sub(r'//.*', '', json_str)
        plants = json.loads(json_str)

    now = datetime.now()
    d = now.day
    m = now.month - 1 # В JS месяцы 0-11
    
    msg = "🌿 *План в саду на сегодня:*\n\n"
    has_tasks = False

    for p in plants:
        task_list = []
        # Логика полива
        if p['waterFreq'] == 1 or d % p['waterFreq'] == 0:
            task_list.append("💧 Полив")
            # Логика подкормки
            if 'feedMonths' in p and m in p['feedMonths']:
                if p['waterFreq'] > 1 or d in [1, 15]:
                    task_list.append(f"🧪 {p.get('feedNote', 'Подкормка')}")
        
        if task_list:
            msg += f"🔹 *{p['name']}*:\n" + "\n".join([f"  — {t}" for t in task_list]) + "\n\n"
            has_tasks = True

    return msg if has_tasks else "🌿 Сегодня в саду выходной. Все отдыхают!"

def send_to_telegram(text):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    tasks_text = get_tasks()
    send_to_telegram(tasks_text)

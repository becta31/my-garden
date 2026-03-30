import os

import requests


def send_to_telegram(text: str):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("ERROR: Нет токена или ID чата")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "MarkdownV2"}

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("✅ Сообщение отправлено!")
            return True
        print(f"❌ Ошибка Telegram: {response.text[:500]}")
        return False
    except Exception as e:
        print(f"❌ Исключение при отправке: {e}")
        return False

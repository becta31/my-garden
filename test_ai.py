import os
import requests

def test_gemini():
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": "Привет! Если ты это читаешь, ответь фразой: Связь установлена"}]}]
    }
    
    print("Отправка тестового запроса...")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        answer = result['candidates'][0]['content']['parts'][0]['text']
        print(f"Успех! Ответ ИИ: {answer}")
        return f"✅ Тест пройден! ИИ говорит: {answer}"
    else:
        print(f"Ошибка! Код: {response.status_code}")
        print(f"Текст ошибки: {response.text}")
        return f"❌ Тест провален. Код: {response.status_code}. Текст: {response.text[:100]}"

def send_to_tg(text):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

if __name__ == "__main__":
    result_text = test_gemini()
    send_to_tg(result_text)

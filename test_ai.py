import os
import requests

def test_gemini():
    # Берем ключ из переменных окружения GitHub
    api_key = os.getenv('GEMINI_API_KEY')
    
    # Тот самый URL, который у тебя работал в curl
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": "Тестовый запрос. Ответь одним словом: ПРИВЕТ"}]}]
    }
    
    print("--- ЗАПУСК ТЕСТА ---")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['candidates'][0]['content']['parts'][0]['text'].strip()
            print(f"УСПЕХ! ИИ ответил: {answer}")
            return f"✅ Gemini на связи! Ответ: {answer}"
        else:
            error_msg = f"ОШИБКА {response.status_code}: {response.text}"
            print(error_msg)
            return f"❌ Ошибка API: {response.status_code}"
            
    except Exception as e:
        print(f"ОШИБКА СЕТИ: {e}")
        return f"❌ Сетевая ошибка: {str(e)[:50]}"

def send_to_tg(text):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text})

if __name__ == "__main__":
    result = test_gemini()
    send_to_tg(result)

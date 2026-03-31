import os
import requests
import json


def get_ai_comment(prompt: str):
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("AI debug: OPENROUTER_API_KEY missing")
        return None

    try:
        payload = {
            "model": "meta-llama/llama-3.2-3b-instruct:free",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты бот-агроном. Дай одну короткую полезную фразу по уходу за комнатными растениями сегодня."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2,
            "top_p": 0.7,
            "max_tokens": 100
        }

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=15,
        )

        print(f"AI debug: status={response.status_code}")

        if response.status_code == 429:
            print("AI debug: rate-limited")
            return None

        response.raise_for_status()
        data = response.json()
        print(f"AI debug: response={data}")

        choices = data.get("choices", [])
        if not choices:
            print("AI debug: no choices")
            return None

        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            text = content.strip()
            print(f"AI debug: content={text!r}")
            return text or None

        print("AI debug: content missing or not string")
        return None

    except Exception as e:
        print(f"AI error: {e}")
        return None

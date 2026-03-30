import os

import requests


def get_ai_comment(prompt: str, timeout: int = 30):
    api_key = os.getenv("CEREBRAS_API_KEY", "").strip()
    if not api_key:
        return None

    url = "https://api.cerebras.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-4-scout-17b-16e-instruct",
        "messages": [
            {
                "role": "system",
                "content": "Ты краткий помощник по уходу за домашними растениями. Дай 1-2 короткие практические фразы по-русски без воды."
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "max_tokens": 120,
        "temperature": 0.4,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return None
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            text = content.strip()
            return text or None
        return None
    except Exception as e:
        print(f"AI error: {e}")
        return None

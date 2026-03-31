import os
import requests


def get_ai_comment(prompt: str):
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "z-ai/glm-4.5-air:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "Ответь по-русски одной очень короткой полезной фразой для ухода за комнатными растениями сегодня."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "reasoning": {
                    "enabled": True,
                    "exclude": True
                },
                "temperature": 0.0,
                "top_p": 0.5,
                "max_tokens": 24
            },
            timeout=12,
        )

        if response.status_code == 429:
            print("AI rate-limited by OpenRouter (429)")
            return None

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

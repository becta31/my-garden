import os
import requests


def get_ai_comment(prompt: str):
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None

    system_prompt = "Ответь по-русски одной короткой практической фразой для ухода за комнатными растениями сегодня. Если полезного совета нет, верни пустую строку."

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "z-ai/glm-4.5-air:free",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "reasoning": {
                    "enabled": true,
                    "exclude": true
                },
                "temperature": 0.1,
                "top_p": 0.7,
                "max_tokens": 40,
            },
            timeout=15,
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

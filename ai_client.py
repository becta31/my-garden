import os
import requests


def get_ai_comment(prompt: str):
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None

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
                        "content": (
                            "Ты помощник по уходу за КОМНАТНЫМИ растениями в помещении. "
                            "Отвечай только по-русски. "
                            "Дай максимум 1 короткую практическую фразу для сегодняшнего ухода. "
                            "Если полезного совета нет, верни пустую строку. "
                            "Используй только переданные данные о погоде, сезоне и общем состоянии. "
                            "Не пиши советы про улицу, окно, сквозняк, батареи, обогреватели, "
                            "перестановку горшков, укрытие растений или помещение, если это не указано явно. "
                            "Не выдумывай риски. Не давай радикальных советов. "
                            "Разрешены только спокойные советы про умеренный полив, контроль сухости грунта, "
                            "тёплую воду и отсутствие резких изменений ухода. "
                            "Стиль: очень коротко, конкретно, без воды."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "max_tokens": 60,
                "temperature": 0.3,
            },
            timeout=20,
        )
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

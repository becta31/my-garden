import os

from cerebras.cloud.sdk import Cerebras


def get_ai_comment(prompt: str):
    api_key = os.getenv("CEREBRAS_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        client = Cerebras(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Ты помощник по уходу за КОМНАТНЫМИ растениями в помещении. Отвечай только по-русски. Дай максимум 1 короткую практическую фразу для сегодняшнего ухода. Если полезного совета нет, верни пустую строку. Используй только переданные данные о погоде, сезоне и общем состоянии. Не пиши советы про улицу, окно, сквозняк, батареи, обогреватели, перестановку горшков, укрытие растений или помещение, если это не указано явно. Не выдумывай риски. Не давай радикальных советов. Разрешены только спокойные советы про умеренный полив, контроль сухости грунта, тёплую воду и отсутствие резких изменений ухода. Стиль: очень коротко, конкретно, без воды.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            model="llama3.1-8b",
        )

        choices = getattr(chat_completion, "choices", None)
        if not choices:
            return None

        first = choices[0]
        message = getattr(first, "message", None)
        if message is None:
            return None

        content = getattr(message, "content", None)
        if isinstance(content, str):
            text = content.strip()
            return text or None

        return None
    except Exception as e:
        print(f"AI error: {e}")
        return None

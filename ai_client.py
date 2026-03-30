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
                    "content": "Ты помощник по уходу за домашними растениями. Отвечай только по-русски. Дай 1-2 очень короткие практические фразы для сегодняшнего ухода. Учитывай только переданные данные о погоде и сезоне. Не выдумывай риски и не давай радикальных советов без явных оснований. Не советуй убирать растения от окна, сокращать или увеличивать полив, если это прямо не следует из данных. Не повторяй очевидные вещи. Стиль: спокойно, конкретно, без воды, без вступлений.",
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

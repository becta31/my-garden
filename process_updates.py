import os
import json
import time
import requests
from datetime import datetime

STATE_FILE = "telegram_state.json"
HISTORY_FILE = "history.json"


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def tg_request(token, method, payload=None, timeout=20):
    url = f"https://api.telegram.org/bot{token}/{method}"
    return requests.post(url, json=payload or {}, timeout=timeout)


def append_history(history, plant_id, action, source="telegram"):
    # action: "water" | "feed"
    date_str = datetime.now().strftime("%Y-%m-%d")
    event = "Полив" if action == "water" else "Подкормка"

    history.setdefault(plant_id, [])
    history[plant_id].append({
        "date": date_str,
        "event": event,
        "note": f"Отмечено в Telegram ({source})"
    })


def main():
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        print("No TELEGRAM_TOKEN")
        return

    # На всякий случай отключаем webhook, иначе getUpdates может не возвращать апдейты
    try:
        tg_request(token, "deleteWebhook", {"drop_pending_updates": False}, timeout=20)
    except Exception as e:
        print("deleteWebhook error:", e)

    state = load_json(STATE_FILE, {"last_update_id": 0})
    history = load_json(HISTORY_FILE, {})

    offset = int(state.get("last_update_id", 0)) + 1

    resp = tg_request(token, "getUpdates", {"offset": offset, "timeout": 0}, timeout=30)
    if resp.status_code != 200:
        print("getUpdates failed:", resp.status_code, resp.text)
        return

    data = resp.json()
    if not data.get("ok"):
        print("getUpdates not ok:", data)
        return

    updates = data.get("result", [])
    if not updates:
        print("No updates")
        return

    changed = False
    max_update_id = state.get("last_update_id", 0)

    for upd in updates:
        uid = upd.get("update_id", 0)
        if uid > max_update_id:
            max_update_id = uid

        cb = upd.get("callback_query")
        if not cb:
            continue

        cb_id = cb.get("id")
        cb_data = cb.get("data", "")  # ожидаем: done:<plant_id>:<action>
        msg = cb.get("message") or {}
        chat_id = (msg.get("chat") or {}).get("id")
        message_id = msg.get("message_id")

        parts = cb_data.split(":")
        if len(parts) != 3 or parts[0] != "done":
            # отвечаем, чтобы не крутилось "loading"
            try:
                tg_request(token, "answerCallbackQuery", {"callback_query_id": cb_id, "text": "Ок"}, timeout=15)
            except Exception:
                pass
            continue

        plant_id = parts[1].strip()
        action = parts[2].strip()  # water/feed

        if action not in ("water", "feed"):
            try:
                tg_request(token, "answerCallbackQuery", {"callback_query_id": cb_id, "text": "Не понял действие"}, timeout=15)
            except Exception:
                pass
            continue

        append_history(history, plant_id, action)
        changed = True

        # подтверждение нажатия
        try:
            txt = "✅ Полив записан" if action == "water" else "🧪 Подкормка записана"
            tg_request(token, "answerCallbackQuery", {"callback_query_id": cb_id, "text": txt, "show_alert": False}, timeout=15)
        except Exception:
            pass

        # (необязательно) обновляем текст сообщения, добавив отметку
        if chat_id and message_id:
            try:
                original_text = msg.get("text", "")
                stamp = "\n\n📝 Отмечено: " + ("Полив ✅" if action == "water" else "Подкормка 🧪")
                new_text = (original_text + stamp) if stamp not in original_text else original_text
                tg_request(token, "editMessageText", {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": new_text
                }, timeout=20)
            except Exception as e:
                print("editMessageText error:", e)

    state["last_update_id"] = max_update_id
    save_json(STATE_FILE, state)

    if changed:
        save_json(HISTORY_FILE, history)
        print("History updated")
    else:
        print("No callback changes")


if __name__ == "__main__":
    main()

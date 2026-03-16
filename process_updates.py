# process_updates.py — ОБНОВЛЕННЫЙ (работает с plants.json)
import os
import json
import re
import requests
from datetime import datetime, timezone

STATE_FILE = "telegram_state.json"
HISTORY_FILE = "history.json"
PLANTS_FILE = "plants.json" # Теперь используем тот же файл, что и основной бот

DEDUP_SECONDS = 60

def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None

# --------- plants.json loader ----------
def load_plants():
    if not os.path.exists(PLANTS_FILE):
        return [], {}
    
    with open(PLANTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Поддержка формата {"plants": [...]} и просто [...]
    if isinstance(data, dict):
        plants = data.get("plants", [])
    elif isinstance(data, list):
        plants = data
    else:
        plants = []

    # Создаем словарь ID -> растение
    by_id = {p.get("id"): p for p in plants if isinstance(p, dict) and p.get("id")}
    return plants, by_id

# --------- state/history helpers ----------
def load_state():
    if not os.path.exists(STATE_FILE):
        return {"last_update_id": 0}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "last_update_id" in data:
            return data
        return {"last_update_id": 0}
    except Exception:
        return {"last_update_id": 0}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def update_last_watered(history, plant_id):
    now_iso = datetime.now(timezone.utc).isoformat()
    if plant_id not in history:
        history[plant_id] = {}
    history[plant_id]["last_watered"] = now_iso
    return history

# --------- telegram helpers ----------
def tg_request(token, method, payload=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    r = requests.post(url, json=payload or {}, timeout=20)
    r.raise_for_status()
    return r.json()

def answer_callback(token, callback_query_id, text="Готово ✅"):
    try:
        tg_request(token, "answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text})
    except Exception:
        pass

def send_message(token, chat_id, text):
    try:
        tg_request(token, "sendMessage", {"chat_id": chat_id, "text": text})
    except Exception:
        pass

def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def match_plant_by_text(plants, text_norm: str):
    for p in plants:
        name = normalize(p.get("name", ""))
        if name and name in text_norm:
            return p
    for p in plants:
        pid = normalize(p.get("id", ""))
        if pid and pid in text_norm:
            return p
    return None

def main():
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Нет TELEGRAM_TOKEN")

    plants, plants_by_id = load_plants()
    state = load_state()
    history = load_history()

    offset = int(state.get("last_update_id", 0)) + 1
    resp = tg_request(token, "getUpdates", {"timeout": 0, "offset": offset})
    updates = resp.get("result", [])

    if not updates:
        return

    max_update_id = int(state.get("last_update_id", 0))

    for upd in updates:
        upd_id = int(upd.get("update_id", 0))
        max_update_id = max(max_update_id, upd_id)

        if "callback_query" in upd:
            cq = upd["callback_query"]
            cqid = cq.get("id")
            data = str(cq.get("data", ""))
            chat_id = (cq.get("message", {}) or {}).get("chat", {}).get("id")

            if data == "help":
                answer_callback(token, cqid, "Нажми ✅ на нужном растении")
                if chat_id:
                    send_message(token, chat_id, "Как отмечать: нажми кнопку ✅ под планом — запись попадёт в историю.")
                continue

            m = re.match(r"^done:(.+)$", data)
            if m:
                plant_id = m.group(1).strip()
                plant = plants_by_id.get(plant_id)
                if plant:
                    update_last_watered(history, plant_id)
                    answer_callback(token, cqid, "Записал ✅")
                else:
                    answer_callback(token, cqid, "Не нашёл растение в базе 😕")
                continue

            answer_callback(token, cqid, "Ок")
            continue

        msg = upd.get("message") or {}
        text = msg.get("text", "")
        if not text:
            continue

        tnorm = normalize(text)

        if "сделано" in tnorm or "done" in tnorm:
            plant = match_plant_by_text(plants, tnorm)
            if plant:
                update_last_watered(history, plant["id"])

    save_history(history)
    save_state({"last_update_id": max_update_id})

if __name__ == "__main__":
    main()

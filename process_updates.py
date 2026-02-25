# process_updates.py (PRO: callback done:<plant_id> + антидубли + history.json + telegram_state.json)
import os
import json
import re
import ast
import requests
from datetime import datetime, timezone

STATE_FILE = "telegram_state.json"
HISTORY_FILE = "history.json"
DATA_FILE = "data.js"

# антидубль: если одинаковое plant_id было отмечено меньше N секунд назад — игнор
DEDUP_SECONDS = 60


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


# --------- data.js parser ----------
def _parse_js_const_array(content: str, const_name: str):
    m = re.search(rf"const\s+{re.escape(const_name)}\s*=\s*(\[[\s\S]*?\])\s*;", content)
    if not m:
        return None

    arr = m.group(1)
    arr = re.sub(r"/\*[\s\S]*?\*/", "", arr)
    arr = re.sub(r"//.*", "", arr)
    arr = re.sub(r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', arr)
    arr = re.sub(r",\s*([}\]])", r"\1", arr)

    return ast.literal_eval(arr)


def load_plants():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    plants = _parse_js_const_array(content, "plantsData")
    if not isinstance(plants, list):
        raise ValueError("plantsData не найден в data.js")
    by_id = {p.get("id"): p for p in plants if p.get("id")}
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
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # history ДОЛЖЕН быть списком
        if isinstance(data, list):
            return data

        # если вдруг был dict — конвертим в список
        if isinstance(data, dict):
            items = data.get("items")
            return items if isinstance(items, list) else []

        return []
    except Exception:
        return []


def save_history(items):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def is_duplicate(history, plant_id: str) -> bool:
    if not history:
        return False
    last = history[-1]
    if not isinstance(last, dict):
        return False
    if last.get("plant_id") != plant_id:
        return False
    last_ts = parse_iso(str(last.get("ts", "")))
    if not last_ts:
        return False
    now = datetime.now(timezone.utc)
    delta = (now - last_ts).total_seconds()
    return delta < DEDUP_SECONDS


def add_history_event(history, plant_id, plant_name, source):
    if is_duplicate(history, plant_id):
        return False
    history.append(
        {
            "ts": utc_now_iso(),
            "plant_id": plant_id,
            "plant_name": plant_name,
            "action": "done",
            "source": source,
        }
    )
    return True


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
    # матч по названию
    for p in plants:
        name = normalize(p.get("name", ""))
        if name and name in text_norm:
            return p
    # матч по id
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

        # 1) callback кнопки
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
                    ok = add_history_event(history, plant_id, plant.get("name", plant_id), source=f"button:{plant_id}")
                    answer_callback(token, cqid, "Записал ✅" if ok else "Уже отмечено ✅")
                else:
                    answer_callback(token, cqid, "Не нашёл растение в базе 😕")
                continue

            answer_callback(token, cqid, "Ок")
            continue

        # 2) текстовые сообщения (fallback)
        msg = upd.get("message") or {}
        text = msg.get("text", "")
        if not text:
            continue

        tnorm = normalize(text)

        if "сделано" in tnorm or "done" in tnorm:
            plant = match_plant_by_text(plants, tnorm)
            if plant:
                add_history_event(history, plant["id"], plant.get("name", plant["id"]), source=text.strip())

    save_history(history)
    save_state({"last_update_id": max_update_id})


if __name__ == "__main__":
    main()

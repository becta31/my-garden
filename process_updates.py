# process_updates.py
import os
import json
import requests
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")

API_URL = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "telegram_state.json"
HISTORY_FILE = "history.json"
DATA_FILE = "data.js"


# ------------------ utils ------------------

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_offset():
    state = load_json(STATE_FILE, {})
    return state.get("update_id", 0)


def save_offset(update_id):
    save_json(STATE_FILE, {"update_id": update_id})


# ------------------ plants ------------------

def load_plants():
    """достаём id и name из data.js"""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    import re, ast

    m = re.search(r"const\s+plantsData\s*=\s*(\[[\s\S]*?\]);", text)
    if not m:
        return []

    arr = m.group(1)
    arr = re.sub(r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', arr)
    plants = ast.literal_eval(arr)

    return plants


def find_plant_by_text(text, plants):
    text = text.lower()

    for p in plants:
        name = p.get("name", "").lower()
        pid = p.get("id", "").lower()

        if pid in text:
            return p

        # грубый поиск по словам
        for word in name.split():
            if len(word) > 4 and word in text:
                return p

    return None


# ------------------ history ------------------

def add_history(plant_id, plant_name):
    history = load_json(HISTORY_FILE, [])

    history.append({
        "plant_id": plant_id,
        "plant_name": plant_name,
        "event": "Полив выполнен",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    save_json(HISTORY_FILE, history)


# ------------------ main ------------------

def main():
    offset = load_offset()

    r = requests.get(
        f"{API_URL}/getUpdates",
        params={"offset": offset + 1, "timeout": 10},
        timeout=20,
    )

    data = r.json()
    if not data.get("ok"):
        print("Telegram error")
        return

    plants = load_plants()
    last_update = offset

    for upd in data.get("result", []):
        last_update = upd["update_id"]

        message = upd.get("message", {})
        text = message.get("text", "")

        if not text:
            continue

        txt = text.lower()

        # ✅ ТВОЙ НОВЫЙ ФОРМАТ
        if "сделано" in txt:
            plant = find_plant_by_text(txt, plants)
            if plant:
                add_history(plant["id"], plant["name"])
                print("Saved:", plant["name"])

    save_offset(last_update)


if __name__ == "__main__":
    main()

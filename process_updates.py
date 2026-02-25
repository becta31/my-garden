import os
import json
import re
import ast
import requests
from datetime import datetime

HISTORY_FILE = "history.json"
STATE_FILE = "telegram_state.json"
DATA_FILE = "data.js"


# ---------- helpers ----------
def _load_json(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            if not raw:
                return default
            return json.loads(raw)
    except Exception:
        return default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize(s: str) -> str:
    s = (s or "").lower().strip()
    s = s.replace("ё", "е")
    # убрать скобки и их содержимое
    s = re.sub(r"\(.*?\)", " ", s)
    # оставить буквы/цифры/пробел
    s = re.sub(r"[^a-zа-я0-9\s]+", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------- parse data.js (plantsData) ----------
def _parse_js_const_array(content: str, const_name: str):
    m = re.search(rf"const\s+{re.escape(const_name)}\s*=\s*(\[[\s\S]*?\])\s*;", content)
    if not m:
        return None
    arr = m.group(1)

    # remove comments
    arr = re.sub(r"/\*[\s\S]*?\*/", "", arr)  # block
    arr = re.sub(r"//.*", "", arr)            # line

    # quote bare keys: { month: 0 } -> { "month": 0 }
    arr = re.sub(r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', arr)

    # trailing commas
    arr = re.sub(r",\s*([}\]])", r"\1", arr)

    return ast.literal_eval(arr)


def load_plants():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    plants = _parse_js_const_array(content, "plantsData")
    if not isinstance(plants, list):
        raise ValueError("Не найден plantsData в data.js")
    return plants


def build_name_index(plants):
    """
    Индекс для поиска растения по тексту пользователя.
    Делаем несколько ключей: полное имя, первая часть до '/', и т.д.
    """
    index = []
    for p in plants:
        pid = p.get("id")
        name = p.get("name", "")
        n_full = normalize(name)
        variants = {n_full}

        # если есть "Лимоны / Цитрусы" -> добавим "лимоны" и "цитрусы"
        if "/" in name:
            parts = [normalize(x) for x in name.split("/") if normalize(x)]
            variants.update(parts)

        # первое слово тоже иногда удобно ("адениум")
        first = n_full.split(" ")[0] if n_full else ""
        if first:
            variants.add(first)

        for v in variants:
            if v:
                index.append((v, pid, name))
    return index


def find_plant_by_text(text: str, index):
    """
    Пытаемся найти лучшее совпадение.
    Стратегия:
      1) если текст содержит вариант целиком -> берем самый длинный вариант
      2) иначе None
    """
    t = normalize(text)
    best = None  # (len_variant, pid, name)
    for variant, pid, name in index:
        if variant and variant in t:
            cand = (len(variant), pid, name)
            if best is None or cand[0] > best[0]:
                best = cand
    if best:
        return {"id": best[1], "name": best[2]}
    return None


# ---------- telegram ----------
def tg_get_updates(token: str, offset: int | None):
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"timeout": 0}
    if offset is not None:
        params["offset"] = offset
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram getUpdates not ok: {data}")
    return data.get("result", [])


def tg_answer_callback(token: str, callback_query_id: str, text: str = "✅ Записал"):
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    try:
        requests.post(url, json={"callback_query_id": callback_query_id, "text": text}, timeout=12)
    except Exception:
        pass


# ---------- history ----------
def load_history_as_list():
    h = _load_json(HISTORY_FILE, default=[])
    # если случайно лежит {}, приводим к []
    if isinstance(h, dict):
        if len(h) == 0:
            return []
        # если вдруг там был формат {"events":[...]}
        if isinstance(h.get("events"), list):
            return h["events"]
        return []
    if isinstance(h, list):
        return h
    return []


def add_history(history_list, plant_id, plant_name, action, source_text=None):
    history_list.append({
        "ts": datetime.now().isoformat(timespec="seconds"),
        "plant_id": plant_id,
        "plant_name": plant_name,
        "action": action,
        "source": source_text or ""
    })


# ---------- main ----------
def main():
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN is empty")

    plants = load_plants()
    index = build_name_index(plants)

    state = _load_json(STATE_FILE, default={"last_update_id": 0})
    last_update_id = int(state.get("last_update_id", 0))
    offset = last_update_id + 1 if last_update_id else None

    updates = tg_get_updates(token, offset=offset)
    if not updates:
        print("No updates")
        return

    history = load_history_as_list()
    max_uid = last_update_id

    for upd in updates:
        uid = upd.get("update_id", 0)
        if uid > max_uid:
            max_uid = uid

        # 1) callback кнопки
        if "callback_query" in upd:
            cq = upd["callback_query"]
            cq_id = cq.get("id")
            data = (cq.get("data") or "").strip()
            # ожидаемые форматы:
            # done|adenium-young
            # done:adenium-young
            plant = None
            action = None

            if data.startswith("done|"):
                action = "done"
                pid = data.split("|", 1)[1].strip()
                plant = next((p for p in plants if p.get("id") == pid), None)
            elif data.startswith("done:"):
                action = "done"
                pid = data.split(":", 1)[1].strip()
                plant = next((p for p in plants if p.get("id") == pid), None)

            if plant and action == "done":
                add_history(history, plant["id"], plant["name"], "done", source_text=f"callback:{data}")
                tg_answer_callback(token, cq_id, "✅ Записал в историю")
            else:
                # если кнопка старая и без plant_id — просто ответим
                if cq_id:
                    tg_answer_callback(token, cq_id, "ℹ️ Кнопка без ID растения (обнови бота)")
            continue

        # 2) обычный текст
        msg = upd.get("message") or upd.get("edited_message")
        if not msg:
            continue

        text = (msg.get("text") or "").strip()
        if not text:
            continue

        # ловим "сделано"
        # примеры: "адениум сделано", "гранат сделано", "фиалки сделано сегодня"
        if "сделано" in normalize(text):
            plant = find_plant_by_text(text, index)
            if plant:
                add_history(history, plant["id"], plant["name"], "done", source_text=text)
                print(f"OK: {plant['name']} -> done")
            else:
                print("WARN: не понял растение из текста:", text)

    # сохраняем history и state
    _save_json(HISTORY_FILE, history)
    _save_json(STATE_FILE, {"last_update_id": max_uid})
    print(f"Saved: {len(history)} events, last_update_id={max_uid}")


if __name__ == "__main__":
    main()

# send_tasks.py (Telegram: per-plant messages + callback buttons + checklist)
import os
import json
import re
import ast
import requests
from datetime import datetime

LAST_WEATHER_FILE = "last_weather.json"


# ---------- Telegram MarkdownV2 (escape) ----------
def md_escape(text) -> str:
    if text is None:
        return ""
    s = str(text)
    s = s.replace("\\", "\\\\")
    return re.sub(r"([_*[\]()~`>#+\-=|{}.!])", r"\\\1", s)


# ---------- Weather memory ----------
def load_last_temp():
    try:
        with open(LAST_WEATHER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("temp")
    except Exception:
        return None


def save_last_temp(temp, city="Moscow"):
    try:
        with open(LAST_WEATHER_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"temp": temp, "city": city, "saved_at": datetime.now().isoformat()},
                f,
                ensure_ascii=False,
            )
    except Exception:
        pass


# ---------- Weather ----------
def get_weather():
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    city = os.getenv("CITY_NAME", "Moscow").strip() or "Moscow"

    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather?"
            f"q={city}&appid={api_key}&units=metric&lang=ru"
        )
        res = requests.get(url, timeout=10).json()
        return {
            "temp": round(res["main"]["temp"]),
            "hum": int(res["main"]["humidity"]),
            "desc": res["weather"][0]["description"],
            "wind": float(res.get("wind", {}).get("speed", 0)),
        }
    except Exception:
        return {"temp": 0, "hum": 50, "desc": "нет данных", "wind": 0}


def weather_comment(weather, month_idx, delta_temp=None):
    temp = weather.get("temp", 0)
    wind = weather.get("wind", 0)

    if delta_temp is not None and abs(delta_temp) >= 8:
        if delta_temp > 0:
            return f"📈 Резкое потепление (+{abs(delta_temp)}°). Не форсируй изменения ухода за один день."
        return f"📉 Резкое похолодание (−{abs(delta_temp)}°). Без резких действий, проветривание аккуратно."

    if wind >= 12:
        return "🌬 Очень сильный ветер. Проветривай коротко, избегай сквозняка у окон."

    if month_idx in [11, 0, 1]:
        if temp <= -15:
            return "🥶 Сильный мороз. Окна открывай кратко; избегай холодного стекла у растений."
        if temp <= -10:
            return "❄️ Мороз. Проветривание делай коротко, без сквозняка."
        if wind >= 9:
            return "🌬 Ветер. При проветривании избегай прямого потока на подоконник."
        return None

    return None


def stage_hint(stage):
    if not stage:
        return None
    s = str(stage).strip().lower()
    if s in ("bloom", "цветение"):
        return "🌸 Режим: цветение — PK (K>N) слабой дозой, без гуматов/янтарки."
    if s in ("foliage", "листва", "рост"):
        return "🌿 Режим: листва — умеренный рост, без резких стимуляций."
    if s in ("recover", "восстановление"):
        return "♻️ Режим: восстановление — без стимуляторов/PK, приоритет корни."
    if s in ("dormant", "покой"):
        return "🛌 Режим: покой — только вода, без подкормок."
    return None


def _text_blob(p):
    parts = []
    for k in ("feedNote", "feedShort", "warning", "name", "category", "location"):
        v = p.get(k)
        if v:
            parts.append(str(v))
    return " ".join(parts).lower()


def _already_covered(blob: str, keywords):
    return any(kw in blob for kw in keywords)


def semi_auto_hint(p, month_idx):
    name = str(p.get("name", "")).lower()
    cat = str(p.get("category", "")).lower()
    stage = str(p.get("stage", "")).lower()
    blob = _text_blob(p)
    hints = []

    if stage in ("recover", "восстановление"):
        if not _already_covered(blob, ["без pk", "без мкф", "восстанов"]):
            hints.append("💡 Восстановление: без МКФ/PK; максимум мягкий Акварин 0.3 г/л редко.")
        return hints[:2]

    if month_idx == 2 and stage in ("foliage", "листва", "рост") and cat in ("fruit", "adenium"):
        if not _already_covered(blob, ["осмокот", "osmocote"]):
            if "цитрус" in name or "лимон" in name:
                hints.append("💡 Старт сезона: можно заложить Осмокот Pro 3–4 г/л субстрата.")
            elif "адениум" in name:
                hints.append("💡 Адениум: Осмокот умеренно (≈3 г/л) и без частых жидких подкормок.")

    return hints[:2]


# ---------- JS parsing ----------
def _parse_js_const_array(content: str, const_name: str):
    m = re.search(rf"const\s+{re.escape(const_name)}\s*=\s*($begin:math:display$\[\\s\\S\]\*\?$end:math:display$)\s*;", content)
    if not m:
        return None

    arr = m.group(1)
    arr = re.sub(r"/\*[\s\S]*?\*/", "", arr)
    arr = re.sub(r"//.*", "", arr)
    arr = re.sub(r'([{$begin:math:display$\,\]\\s\*\)\(\[A\-Za\-z\_\]\[A\-Za\-z0\-9\_\]\*\)\\s\*\:\'\, r\'\\1\"\\2\"\:\'\, arr\)
    arr \= re\.sub\(r\"\,\\s\*\(\[\}$end:math:display$])", r"\1", arr)
    return ast.literal_eval(arr)


def parse_data_js(path="data.js"):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    plants = _parse_js_const_array(content, "plantsData")
    if not isinstance(plants, list):
        raise ValueError("Не найден массив plantsData в data.js")

    cal = _parse_js_const_array(content, "careCalendar")
    if cal is not None and not isinstance(cal, list):
        cal = None

    return plants, cal


# ---------- Checklist logic ----------
def has_feed_today(p, month_idx):
    return month_idx in p.get("feedMonths", [])


def pick_feed_text(p) -> str:
    return (p.get("feedShort") or p.get("feedNote") or "").strip()


# ---------- Telegram send helpers ----------
def tg_send_message(token, chat_id, text, reply_markup=None, parse_mode="MarkdownV2"):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return requests.post(url, json=payload, timeout=20)


def send_to_telegram(plants_today, header_text):
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return

    # 1) Header (без кнопок)
    try:
        r0 = tg_send_message(token, chat_id, header_text, reply_markup=None, parse_mode="MarkdownV2")
        if r0.status_code != 200:
            # fallback plain
            tg_send_message(token, chat_id, header_text.replace("\\", ""), reply_markup=None, parse_mode=None)
    except Exception:
        pass

    # 2) Каждое растение — отдельным сообщением с кнопками
    for item in plants_today:
        try:
            text = item["text_md"]
            kb = item["keyboard"]

            r = tg_send_message(token, chat_id, text, reply_markup=kb, parse_mode="MarkdownV2")
            if r.status_code == 200:
                continue

            # fallback plain
            tg_send_message(token, chat_id, text.replace("\\", ""), reply_markup=kb, parse_mode=None)
        except Exception:
            pass


# ---------- Build messages ----------
def build_messages():
    weather = get_weather()
    city = os.getenv("CITY_NAME", "Moscow").strip() or "Moscow"

    plants, _ = parse_data_js("data.js")

    now = datetime.now()
    day, month_idx = now.day, now.month - 1

    last_temp = load_last_temp()
    delta_temp = None
    if last_temp is not None:
        try:
            delta_temp = int(weather.get("temp", 0)) - int(last_temp)
        except Exception:
            delta_temp = None

    comment = weather_comment(weather, month_idx, delta_temp=delta_temp)

    header = f"🌿 *{md_escape('ПЛАН САДА — ' + now.strftime('%d.%m'))}*\n"
    header += (
        f"🌡 {md_escape('Улица')}: {md_escape(weather['temp'])}°C | 💧 {md_escape(weather['hum'])}% | "
        f"{md_escape(str(weather['desc']).capitalize())} | 💨 {md_escape(weather.get('wind', 0))} м/с\n\n"
    )
    header += f"🤖 {md_escape(comment) if comment else md_escape('Погодные корректировки не требуются.')}\n"

    plants_today = []

    for p in plants:
        wf = int(p.get("waterFreq", 99))
        if wf != 1 and day % wf != 0:
            continue

        plant_id = str(p.get("id", "")).strip()
        if not plant_id:
            # без id кнопки нельзя нормально логировать
            continue

        feed_today = has_feed_today(p, month_idx)
        feed_text = pick_feed_text(p) if feed_today else ""

        name_up = str(p.get("name", "?")).upper()
        freq_text = "ежедневно" if wf == 1 else f"раз в {wf} дн."

        text = f"📍 *{md_escape(name_up)}*\n"
        text += f"🗓 {md_escape('Частота')}: {md_escape(freq_text)}\n\n"
        text += f"🟢 *{md_escape('СДЕЛАТЬ СЕГОДНЯ')}:*\n"
        text += f"{md_escape('☑ 💧 Полить')}\n"
        if feed_today:
            text += f"{md_escape('☑ 🧪 Подкормить')}\n"

        st = stage_hint(p.get("stage"))
        if st:
            text += f"\n🔎 {md_escape('Подсказка')}:\n_{md_escape(st)}_\n"

        for h in semi_auto_hint(p, month_idx):
            text += f"_{md_escape(h)}_\n"

        if p.get("warning"):
            text += f"\n⚠️ _{md_escape(str(p['warning']))}_\n"

        if feed_today and feed_text:
            text += f"\n💊 *{md_escape('Формула сегодня')}:*\n{md_escape(feed_text)}\n"

        # Кнопки: полив всегда, подкормка — только если она нужна сегодня
        row = [{"text": "✅ Полил", "callback_data": f"done:{plant_id}:water"}]
        if feed_today:
            row.append({"text": "🧪 Подкормил", "callback_data": f"done:{plant_id}:feed"})

        keyboard = {"inline_keyboard": [row]}

        plants_today.append({"text_md": text, "keyboard": keyboard})

    save_last_temp(weather.get("temp", 0), city=city)
    return header, plants_today


if __name__ == "__main__":
    header_text, plants_today = build_messages()
    send_to_telegram(plants_today, header_text)

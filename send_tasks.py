# send_tasks.py (Level 2: полуавтомат + антидубль + FIX парсинга JS-ключей)
import os
import json
import re
import ast
import requests
from datetime import datetime

LAST_WEATHER_FILE = "last_weather.json"


# ---------- Weather memory (delta-temp trigger) ----------
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
    """
    1 строка, только если есть триггер.
    Москва: годовой режим + резкие качели (delta >= 8°C).
    """
    temp = weather.get("temp", 0)
    wind = weather.get("wind", 0)

    # 0) Резкие качели температуры
    if delta_temp is not None and abs(delta_temp) >= 8:
        if delta_temp > 0:
            return f"📈 Резкое потепление (+{abs(delta_temp)}°). Не форсируй изменения ухода за один день."
        else:
            return f"📉 Резкое похолодание (−{abs(delta_temp)}°). Без резких действий, проветривание аккуратно."

    # 1) Очень сильный ветер — круглый год
    if wind >= 12:
        return "🌬 Очень сильный ветер. Проветривай коротко, избегай сквозняка у окон."

    # ЗИМА: Дек–Фев
    if month_idx in [11, 0, 1]:
        if temp <= -15:
            return "🥶 Сильный мороз. Окна открывай кратко; избегай холодного стекла у растений."
        if temp <= -10:
            return "❄️ Мороз. Проветривание делай коротко, без сквозняка."
        if wind >= 9:
            return "🌬 Ветер. При проветривании избегай прямого потока на подоконник."
        return None

    # ВЕСНА: Мар–Май
    if month_idx in [2, 3, 4]:
        if month_idx in [2, 3] and temp <= -2:
            return "⚠️ Возврат холода. Не форсируй сезонные изменения ухода."
        if month_idx == 2 and temp >= 12:
            return "🌤 Раннее потепление. Переход к весеннему режиму делай постепенно."
        if month_idx in [3, 4] and temp >= 20:
            return "🌤 Резкое тепло. Не меняй уход резко: делай переход плавно."
        if wind >= 9:
            return "🌬 Ветреный день. Проветривай аккуратно, избегай сквозняка."
        return None

    # ЛЕТО: Июн–Авг
    if month_idx in [5, 6, 7]:
        if temp >= 32:
            return "☀️ Сильная жара. Проверяй пересыхание субстрата чаще обычного."
        if temp >= 28:
            return "☀️ Жарко. Полив ориентируй по субстрату, не по календарю."
        return None

    # ОСЕНЬ: Сен–Ноя
    if month_idx in [8, 9, 10]:
        if month_idx == 8 and temp <= 6:
            return "🍂 Раннее похолодание. Переход к более спокойному режиму делай постепенно."
        if month_idx in [9, 10] and temp <= 0:
            return "🍂 Первый минус. Сокращай активные действия по уходу постепенно."
        if wind >= 9:
            return "🌬 Ветер. Проветривай коротко, избегай сквозняка у окон."
        return None

    return None


# ---------- Stage hint ----------
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


# ---------- Level 2 hints (semi-auto) ----------
def _text_blob(p):
    parts = []
    for k in ("feedNote", "warning", "name", "category", "location"):
        v = p.get(k)
        if v:
            parts.append(str(v))
    return " ".join(parts).lower()


def _already_covered(blob: str, keywords):
    return any(kw in blob for kw in keywords)


def semi_auto_hint(p, month_idx):
    """
    0–2 коротких подсказки про удобрения/режим.
    Антидубль: если ключевые слова уже есть в feedNote/warning — не повторяем.
    """
    name = str(p.get("name", "")).lower()
    cat = str(p.get("category", "")).lower()
    stage = str(p.get("stage", "")).lower()
    blob = _text_blob(p)

    hints = []

    # Dormant
    if stage in ("dormant", "покой"):
        if ("гранат" in name or "pomegranate" in name) and month_idx in [2, 3]:
            if not _already_covered(blob, ["акварин", "0.7", "1 г/л", "1г/л"]):
                hints.append("💡 Гранат: при появлении листа верни Акварин 0.7–1 г/л раз в 14 дней.")
        else:
            if not _already_covered(blob, ["без подкорм", "без удоб", "только вода"]):
                hints.append("💡 Покой: без подкормок; питание возвращаем только при явном росте.")
        return hints[:2]

    # Recover
    if stage in ("recover", "восстановление"):
        if not _already_covered(blob, ["без pk", "без мкф", "восстанов"]):
            hints.append("💡 Восстановление: без МКФ/PK; максимум мягкий Акварин 0.3 г/л редко.")
        return hints[:2]

    # Osmocote (March)
    if month_idx == 2 and stage in ("foliage", "листва", "рост"):
        if cat in ("fruit", "adenium"):
            if not _already_covered(blob, ["осмокот", "osmocote"]):
                if "цитрус" in name or "лимон" in name:
                    hints.append("💡 Старт сезона: можно заложить Осмокот Pro 3–4 г/л субстрата.")
                elif "адениум" in name:
                    hints.append("💡 Адениум: Осмокот умеренно (≈3 г/л) и без частых жидких подкормок.")

    # Aquarin (growth season)
    if stage in ("foliage", "листва", "рост") and month_idx in [2, 3, 4, 5]:
        if cat not in ("cactus", "succulent"):
            if not _already_covered(blob, ["акварин", "18-18-18", "0.5", "1 г/л", "1г/л"]):
                hints.append("💡 Рост: Акварин 0.5–1 г/л раз в 2–3 недели по активности роста.")
        else:
            if not _already_covered(blob, ["0.3", "0.5", "раз в 3", "3–4"]):
                hints.append("💡 Суккуленты: питание редко (0.3–0.5 г/л раз в 3–4 недели).")

    # MKF (bloom targets)
    bloom_targets = ("фиал" in name) or ("глокс" in name) or ("каланхо" in name)
    if stage in ("bloom", "цветение") and bloom_targets and month_idx in [3, 4, 5, 6, 7]:
        if not _already_covered(blob, ["мкф", "монофосфат", "0.5", "1 г/л", "1г/л"]):
            hints.append("💡 По бутонам: МКФ 0.5–1 г/л курсом 2–3 полива (не постоянно).")

    # Orchid gentle reminder
    if "орхиде" in name and stage in ("foliage", "листва", "рост") and month_idx in [2, 3, 4, 5, 6, 7]:
        if not _already_covered(blob, ["0.3", "0.5", "раз в 2", "2–3 недели"]):
            hints.append("💡 Орхидея: дозы мягкие (0.3–0.5 г/л) и редко (раз в 2–3 недели).")

    return hints[:2]


# ---------- data.js parsing (plantsData + careCalendar) ----------
def _parse_js_const_array(content: str, const_name: str):
    """
    FIX: понимает JS-объекты с ключами без кавычек:
      { month: 0, title: "...", rules: [...] }
    превращая их в:
      { "month": 0, "title": "...", "rules": [...] }
    """
    m = re.search(rf"const\s+{re.escape(const_name)}\s*=\s*(\[[\s\S]*?\])\s*;", content)
    if not m:
        return None

    arr = m.group(1)

    # remove comments
    arr = re.sub(r"/\*[\s\S]*?\*/", "", arr)  # block comments
    arr = re.sub(r"//.*", "", arr)            # line comments

    # quote bare object keys: { month: 0 } -> { "month": 0 }
    # also works after commas / array openings: , month: ... / [ { month: ... } ]
    arr = re.sub(r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', arr)

    # remove trailing commas before } or ]
    arr = re.sub(r",\s*([}\]])", r"\1", arr)

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


# ---------- Main message building ----------
def get_tasks():
    weather = get_weather()
    city = os.getenv("CITY_NAME", "Moscow").strip() or "Moscow"

    try:
        plants, cal = parse_data_js("data.js")

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

        msg = f"🌿 *ПЛАН САДА — {now.strftime('%d.%m')}*\n"
        msg += (
            f"🌡 Улица: {weather['temp']}°C | 💧 {weather['hum']}% | "
            f"{str(weather['desc']).capitalize()} | 💨 {weather.get('wind', 0)} м/с\n\n"
        )

        if comment:
            msg += f"🤖 {comment}\n"
        else:
            msg += "🤖 Погодные корректировки не требуются.\n"

        # Monthly calendar (only 1st)
        if now.day == 1 and cal:
            cur = next((x for x in cal if x.get("month") == month_idx), None)
            if cur:
                msg += f"\n📅 *{cur.get('title','План месяца')}*\n"
                for r in cur.get("rules", [])[:3]:
                    msg += f"• {r}\n"
                msg += "\n"

        msg += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"

        tasks_count = 0
        for p in plants:
            if day % p.get("waterFreq", 99) == 0:
                tasks_count += 1
                msg += f"📍 *{p.get('name','?').upper()}*\n"

                task_line = "💧 Полив"

                if month_idx in p.get("feedMonths", []):
                    if p.get("waterFreq", 1) > 1 or day in [1, 15]:
                        feed_info = p.get("feedNote", "Удобрение")
                        task_line += f" + 🧪 *{feed_info}*"

                msg += f"{task_line}\n"

                st = stage_hint(p.get("stage"))
                if st:
                    msg += f"└ _{st}_\n"

                # Level 2 hints (anti-duplicate)
                for h in semi_auto_hint(p, month_idx):
                    msg += f"└ _{h}_\n"

                if "warning" in p and p["warning"]:
                    short_warn = str(p["warning"]).replace("Мороз за окном! ", "❄️ ")
                    msg += f"└ _{short_warn}_\n"

                msg += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"

        if tasks_count > 0:
            msg += f"\n✅ *Всего к поливу: {tasks_count}*"
        else:
            msg += "\n🌿 *Сегодня по расписанию только отдых!*"

        save_last_temp(weather.get("temp", 0), city=city)

        return msg

    except Exception as e:
        return f"Ошибка парсинга базы: {e}"


def send_to_telegram(text):
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": [[{"text": "✅ Сделано!", "callback_data": "done"}]]},
    }
    try:
        requests.post(url, json=payload, timeout=12)
    except Exception:
        pass


if __name__ == "__main__":
    send_to_telegram(get_tasks())

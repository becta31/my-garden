# send_tasks.py (Checklist + MarkdownV2 + fallback + JS parser + FEED MEMORY mode 2)
import os
import json
import re
import ast
import requests
from datetime import datetime, date

LAST_WEATHER_FILE = "last_weather.json"
FEED_MEMORY_FILE = "feed_memory.json"


# ---------- Telegram MarkdownV2 (escape) ----------
MDV2_SPECIALS_RE = re.compile(r"([_*\[\]()~`>#+\-=|{}.!])")

def md_escape(text) -> str:
    """
    Escape для Telegram MarkdownV2.
    Экранируем backslash и спецсимволы: _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    if text is None:
        return ""
    s = str(text)
    s = s.replace("\\", "\\\\")  # backslash first
    return MDV2_SPECIALS_RE.sub(r"\\\1", s)


# ---------- Feed memory ----------
def load_feed_memory():
    try:
        with open(FEED_MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_feed_memory(mem):
    try:
        with open(FEED_MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(mem, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _today_iso() -> str:
    return date.today().isoformat()


def _days_since(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        d = date.fromisoformat(iso_date)
        return (date.today() - d).days
    except Exception:
        return None


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
    temp = weather.get("temp", 0)
    wind = weather.get("wind", 0)

    if delta_temp is not None and abs(delta_temp) >= 8:
        if delta_temp > 0:
            return f"📈 Резкое потепление (+{abs(delta_temp)}°). Не форсируй изменения ухода за один день."
        return f"📉 Резкое похолодание (−{abs(delta_temp)}°). Без резких действий, проветривание аккуратно."

    if wind >= 12:
        return "🌬 Очень сильный ветер. Проветривай коротко, избегай сквозняка у окон."

    # зима
    if month_idx in [11, 0, 1]:
        if temp <= -15:
            return "🥶 Сильный мороз. Окна открывай кратко; избегай холодного стекла у растений."
        if temp <= -10:
            return "❄️ Мороз. Проветривание делай коротко, без сквозняка."
        if wind >= 9:
            return "🌬 Ветер. При проветривании избегай прямого потока на подоконник."
        return None

    # весна
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

    # лето
    if month_idx in [5, 6, 7]:
        if temp >= 32:
            return "☀️ Сильная жара. Проверяй пересыхание субстрата чаще обычного."
        if temp >= 28:
            return "☀️ Жарко. Полив ориентируй по субстрату, не по календарю."
        return None

    # осень
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


# ---------- Level 2 hints (semi-auto + anti-duplicate) ----------
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

    if stage in ("dormant", "покой"):
        if ("гранат" in name or "pomegranate" in name) and month_idx in [2, 3]:
            if not _already_covered(blob, ["акварин", "0.7", "1 г/л", "1г/л"]):
                hints.append("💡 Гранат: при появлении листа верни Акварин 0.7–1 г/л раз в 14 дней.")
        else:
            if not _already_covered(blob, ["без подкорм", "без удоб", "только вода"]):
                hints.append("💡 Покой: без подкормок; питание возвращаем только при явном росте.")
        return hints[:2]

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

    if stage in ("foliage", "листва", "рост") and month_idx in [2, 3, 4, 5]:
        if cat not in ("cactus", "succulent"):
            if not _already_covered(blob, ["акварин", "18-18-18", "0.5", "1 г/л", "1г/л"]):
                hints.append("💡 Рост: Акварин 0.5–1 г/л раз в 2–3 недели по активности роста.")
        else:
            if not _already_covered(blob, ["0.3", "0.5", "3–4 недели", "3-4 недели"]):
                hints.append("💡 Суккуленты: питание редко (0.3–0.5 г/л раз в 3–4 недели).")

    bloom_targets = ("фиал" in name) or ("глокс" in name) or ("каланхо" in name)
    if stage in ("bloom", "цветение") and bloom_targets and month_idx in [3, 4, 5, 6, 7]:
        if not _already_covered(blob, ["мкф", "монофосфат", "0.5", "1 г/л", "1г/л"]):
            hints.append("💡 По бутонам: МКФ 0.5–1 г/л курсом 2–3 полива (не постоянно).")

    if "орхиде" in name and stage in ("foliage", "листва", "рост") and month_idx in [2, 3, 4, 5, 6, 7]:
        if not _already_covered(blob, ["0.3", "0.5", "2–3 недели", "2-3 недели"]):
            hints.append("💡 Орхидея: дозы мягкие (0.3–0.5 г/л) и редко (раз в 2–3 недели).")

    return hints[:2]


# ---------- data.js parsing (plantsData + careCalendar) ----------
def _parse_js_const_array(content: str, const_name: str):
    """
    Парсит массив из data.js:
      const plantsData = [ ... ];
      const careCalendar = [ ... ];
    Поддерживает ключи без кавычек: { month: 0, title: "...", rules: [...] }
    """
    m = re.search(rf"const\s+{re.escape(const_name)}\s*=\s*(\[[\s\S]*?\])\s*;", content)
    if not m:
        return None

    arr = m.group(1)
    arr = re.sub(r"/\*[\s\S]*?\*/", "", arr)
    arr = re.sub(r"//.*", "", arr)

    # { month: 0 } -> { "month": 0 }
    arr = re.sub(r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', arr)

    # trailing commas
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


# ---------- Feeding logic (MODE 2: memory-based) ----------
def feed_interval_days(p) -> int:
    """
    Насколько часто можно подкармливать (по умолчанию).
    Можно позже сделать это настройкой в data.js.
    """
    cat = str(p.get("category", "")).lower()
    stage = str(p.get("stage", "")).lower()

    if stage in ("dormant", "покой"):
        return 10**9  # никогда
    if stage in ("recover", "восстановление"):
        return 21
    if cat in ("cactus", "succulent"):
        return 21
    if cat == "orchid":
        return 21
    if stage in ("bloom", "цветение"):
        return 14
    return 14


def choose_feed_today(p, month_idx, mem):
    """
    Возвращает (feed_key, feed_text) или (None, None)
    """
    pid = p.get("id")
    if not pid:
        return None, None

    # только в месяцы подкормок
    if month_idx not in p.get("feedMonths", []):
        return None, None

    stage = str(p.get("stage", "")).lower()
    cat = str(p.get("category", "")).lower()
    name = str(p.get("name", "")).lower()

    # покой — никогда
    if stage in ("dormant", "покой"):
        return None, None

    last = mem.get(pid, {})
    days = _days_since(last.get("last_date"))
    if days is None:
        days = 10**9

    if days < feed_interval_days(p):
        return None, None  # рано

    last_key = last.get("last_feed")

    # приоритет feedShort, если есть (как “подсказка”), но мы всё равно решаем “сегодня / нет”
    feed_short = (p.get("feedShort") or "").strip()

    # цветение: чередуем MKF и Акварин
    if stage in ("bloom", "цветение"):
        if last_key != "mkf":
            return "mkf", (feed_short or "МКФ 0.5–1 г/л (курс 2–3 полива по бутонам)")
        return "aquarin_bloom", (feed_short or "Акварин 0.5–0.7 г/л (½ дозы)")

    # кактусы/сеянцы: чередуем Bona и янтарку
    if cat in ("cactus", "succulent"):
        if last_key != "bona":
            return "bona", "Bona Forte 1 мл/л"
        return "succinic", "Янтарка 0.1 г/л"

    # орхидеи: мягко и редко
    if cat == "orchid":
        return "orchid", (feed_short or "Акварин 0.3–0.5 г/л (½ дозы) раз в 2–3 недели")

    # цитрусы: чередуем гумат и янтарку
    if "лимон" in name or "цитрус" in name or cat == "fruit":
        if last_key != "humate":
            return "humate", "Гумат калия 1 мл/л"
        return "succinic", "Янтарка 0.5 г/л"

    # по умолчанию
    return "aquarin", (feed_short or "Акварин 0.5–1 г/л")


# ---------- Main message building ----------
def get_tasks():
    weather = get_weather()
    city = os.getenv("CITY_NAME", "Moscow").strip() or "Moscow"

    try:
        plants, cal = parse_data_js("data.js")
        feed_mem = load_feed_memory()
        feed_mem_changed = False

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

        msg = f"🌿 *{md_escape('ПЛАН САДА — ' + now.strftime('%d.%m'))}*\n"
        msg += (
            f"🌡 {md_escape('Улица')}: {md_escape(weather['temp'])}°C | 💧 {md_escape(weather['hum'])}% | "
            f"{md_escape(str(weather['desc']).capitalize())} | 💨 {md_escape(weather.get('wind', 0))} м/с\n\n"
        )
        msg += f"🤖 {md_escape(comment) if comment else md_escape('Погодные корректировки не требуются.')}\n"

        # monthly calendar only on 1st
        if now.day == 1 and cal:
            cur = next((x for x in cal if x.get("month") == month_idx), None)
            if cur:
                msg += f"\n📅 *{md_escape(cur.get('title','План месяца'))}*\n"
                for r in cur.get("rules", [])[:3]:
                    msg += f"• {md_escape(r)}\n"
                msg += "\n"

        msg += md_escape("⎯" * 16) + "\n"

        tasks_count = 0
        for p in plants:
            if day % p.get("waterFreq", 99) != 0:
                continue

            tasks_count += 1
            name_up = str(p.get("name", "?")).upper()

            # decide feed today (MODE 2)
            feed_key, feed_text = choose_feed_today(p, month_idx, feed_mem)
            feed_today = bool(feed_text)

            actions = ["☑ 💧 Полить"]
            if feed_today:
                actions.append("☑ 🧪 Подкормить")

            msg += f"\n📍 *{md_escape(name_up)}*\n"
            msg += f"🟢 *{md_escape('СДЕЛАТЬ СЕГОДНЯ')}:*\n"
            for a in actions:
                msg += f"{md_escape(a)}\n"

            if feed_today:
                msg += f"\n💊 *{md_escape('Подкормка сегодня')}:*\n{md_escape(feed_text)}\n"

                pid = p.get("id")
                if pid:
                    feed_mem[pid] = {
                        "last_feed": feed_key,
                        "last_date": _today_iso(),
                    }
                    feed_mem_changed = True

            # hints
            st = stage_hint(p.get("stage"))
            has_any_hints = False
            if st:
                msg += f"\n🔎 {md_escape('Подсказки')}:\n"
                msg += f"└ _{md_escape(st)}_\n"
                has_any_hints = True

            for h in semi_auto_hint(p, month_idx):
                if not has_any_hints:
                    msg += f"\n🔎 {md_escape('Подсказки')}:\n"
                    has_any_hints = True
                msg += f"└ _{md_escape(h)}_\n"

            if p.get("warning"):
                if not has_any_hints:
                    msg += f"\n🔎 {md_escape('Подсказки')}:\n"
                msg += f"└ _{md_escape(str(p['warning']))}_\n"

            msg += md_escape("┈" * 16) + "\n"

        if tasks_count > 0:
            msg += f"\n✅ *{md_escape('Всего задач сегодня')}: {md_escape(tasks_count)}*"
        else:
            msg += f"\n🌿 *{md_escape('Сегодня по расписанию только отдых!')}*"

        if feed_mem_changed:
            save_feed_memory(feed_mem)

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

    # 1) Try MarkdownV2
    payload_md = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "MarkdownV2",
        "reply_markup": {"inline_keyboard": [[{"text": "✅ Сделано!", "callback_data": "done"}]]},
    }

    try:
        r = requests.post(url, json=payload_md, timeout=12)
        if r.status_code == 200:
            return

        print("Telegram error (MarkdownV2):", r.status_code, r.text)

        # 2) Fallback to plain text
        payload_plain = {
            "chat_id": chat_id,
            "text": text.replace("\\", ""),
            "reply_markup": {"inline_keyboard": [[{"text": "✅ Сделано!", "callback_data": "done"}]]},
        }
        r2 = requests.post(url, json=payload_plain, timeout=12)
        if r2.status_code != 200:
            print("Telegram error (plain):", r2.status_code, r2.text)

    except Exception as e:
        print("Telegram request exception:", e)


if __name__ == "__main__":
    send_to_telegram(get_tasks())

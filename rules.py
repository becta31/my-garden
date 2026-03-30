from datetime import datetime


def feeding_allowed_by_stage(stage: str) -> bool:
    stage = str(stage or "").strip().lower()
    return stage not in ("dormant", "покой", "recover", "восстановление")


def check_condition(plant: dict, cond: str) -> bool:
    flags = plant.get("flags", {}) if isinstance(plant.get("flags"), dict) else {}
    cond = str(cond or "").strip().lower()

    if cond == "buds":
        return bool(flags.get("buds", False))
    if cond == "flower_spike":
        return bool(flags.get("flower_spike", False))
    if cond == "active_growth":
        return bool(flags.get("active_growth", True))

    return True


def get_feed_due_status(plant: dict, feed: dict, feed_history: dict, now_utc: datetime, parse_iso_dt):
    plant_id = plant.get("id", "unknown")
    stage = str(plant.get("stage", "")).strip().lower()
    month = now_utc.month

    feed_id = feed.get("id", "feed")
    feed_name = feed.get("name", "Подкормка")
    dose = feed.get("dose", "по инструкции")
    interval_days = int(feed.get("intervalDays", 999))
    months = feed.get("months", [])
    only_stages = [str(x).strip().lower() for x in feed.get("onlyStages", [])]
    conditions = [str(x).strip().lower() for x in feed.get("conditions", [])]

    if not feeding_allowed_by_stage(stage):
        return {
            "due": False,
            "message": f"{feed_name} — сейчас нельзя, растение в режиме покоя/восстановления"
        }

    if months and month not in months:
        return {
            "due": False,
            "message": f"{feed_name} — не сезон"
        }

    if only_stages and stage not in only_stages:
        return {
            "due": False,
            "message": f"{feed_name} — не подходит для текущей стадии"
        }

    for cond in conditions:
        if not check_condition(plant, cond):
            if cond == "buds":
                return {
                    "due": False,
                    "message": f"{feed_name} — только если есть бутоны"
                }
            if cond == "flower_spike":
                return {
                    "due": False,
                    "message": f"{feed_name} — только если есть цветонос"
                }
            return {
                "due": False,
                "message": f"{feed_name} — пока не выполнены условия"
            }

    plant_feed_history = feed_history.get(plant_id, {})
    feed_entry = plant_feed_history.get(feed_id, {}) if isinstance(plant_feed_history, dict) else {}
    last_done = parse_iso_dt(feed_entry.get("last_done"))

    if last_done is None:
        return {
            "due": True,
            "message": f"{feed_name} — {dose}, сделать сегодня"
        }

    days_passed = (now_utc - last_done).days
    remaining = interval_days - days_passed

    if remaining > 0:
        return {
            "due": False,
            "message": f"{feed_name} — {dose}, через {remaining} дн\\."
        }

    return {
        "due": True,
        "message": f"{feed_name} — {dose}, сделать сегодня"
    }


def build_plant_block(plant: dict, feed_history: dict, now_utc: datetime, md_escape, parse_iso_dt):
    name = plant.get("name", "Без имени")
    stage = str(plant.get("stage", "")).strip().lower()
    feeds = plant.get("feeds", [])

    lines = [
        f"📍 *{md_escape(name)}*",
        "💧 *Полив*"
    ]

    due_feeds = []

    if stage in ("dormant", "покой"):
        lines.append("❄️ Режим покоя: *только вода*")
    elif stage in ("recover", "восстановление"):
        lines.append("🚑 Восстановление: без удобрений")
    else:
        if isinstance(feeds, list):
            for feed in feeds:
                if not isinstance(feed, dict):
                    continue
                status = get_feed_due_status(plant, feed, feed_history, now_utc, parse_iso_dt)
                lines.append(f"🧪 {md_escape(status['message'])}")
                if status["due"]:
                    due_feeds.append(feed.get("id"))

    return "\n".join(lines), due_feeds

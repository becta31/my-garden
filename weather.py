import os

import requests


def get_weather():
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    city = os.getenv("CITY_NAME", "Moscow").strip() or "Moscow"

    if not api_key:
        return {
            "available": False,
            "temp": None,
            "hum": None,
            "desc": "нет данных",
            "wind": None,
            "city": city,
        }

    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={api_key}&units=metric&lang=ru"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        res = response.json()

        if not isinstance(res, dict):
            raise ValueError("Некорректный ответ API")

        return {
            "available": True,
            "temp": round(res.get("main", {}).get("temp", 0)),
            "hum": int(res.get("main", {}).get("humidity", 0)),
            "desc": res.get("weather", [{}])[0].get("description", "нет данных"),
            "wind": float(res.get("wind", {}).get("speed", 0)),
            "city": city,
        }
    except Exception as e:
        print(f"Ошибка погоды: {e}")
        return {
            "available": False,
            "temp": None,
            "hum": None,
            "desc": "нет данных",
            "wind": None,
            "city": city,
        }

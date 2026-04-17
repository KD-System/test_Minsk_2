from datetime import datetime
from urllib.request import urlopen
import json

from flask import Flask, render_template

app = Flask(__name__)

MINSK_LAT = 53.9006
MINSK_LON = 27.5590
API_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={MINSK_LAT}&longitude={MINSK_LON}"
    "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
    "is_day,precipitation,weather_code,wind_speed_10m,wind_direction_10m,pressure_msl"
    "&hourly=temperature_2m,weather_code,precipitation_probability"
    "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum"
    "&timezone=Europe%2FMinsk&forecast_days=7"
)

WEATHER_CODES = {
    0: ("Ясно", "sun"),
    1: ("Преимущественно ясно", "sun"),
    2: ("Переменная облачность", "cloud-sun"),
    3: ("Пасмурно", "cloud"),
    45: ("Туман", "fog"),
    48: ("Изморозь", "fog"),
    51: ("Лёгкая морось", "drizzle"),
    53: ("Морось", "drizzle"),
    55: ("Сильная морось", "drizzle"),
    56: ("Ледяная морось", "drizzle"),
    57: ("Сильная ледяная морось", "drizzle"),
    61: ("Небольшой дождь", "rain"),
    63: ("Дождь", "rain"),
    65: ("Сильный дождь", "rain"),
    66: ("Ледяной дождь", "rain"),
    67: ("Сильный ледяной дождь", "rain"),
    71: ("Небольшой снег", "snow"),
    73: ("Снег", "snow"),
    75: ("Сильный снег", "snow"),
    77: ("Снежные зёрна", "snow"),
    80: ("Ливни", "rain"),
    81: ("Сильные ливни", "rain"),
    82: ("Очень сильные ливни", "rain"),
    85: ("Снежные ливни", "snow"),
    86: ("Сильные снежные ливни", "snow"),
    95: ("Гроза", "storm"),
    96: ("Гроза с градом", "storm"),
    99: ("Сильная гроза с градом", "storm"),
}

WIND_DIRECTIONS = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def describe(code):
    return WEATHER_CODES.get(code, ("Неизвестно", "cloud"))


def wind_dir(degrees):
    idx = int((degrees + 22.5) // 45) % 8
    return WIND_DIRECTIONS[idx]


def fetch_weather():
    with urlopen(API_URL, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def build_view(data):
    current = data["current"]
    code = current["weather_code"]
    label, icon = describe(code)

    now = {
        "temperature": round(current["temperature_2m"]),
        "feels_like": round(current["apparent_temperature"]),
        "humidity": current["relative_humidity_2m"],
        "precipitation": current["precipitation"],
        "pressure": round(current["pressure_msl"] * 0.75006),
        "wind_speed": round(current["wind_speed_10m"]),
        "wind_dir": wind_dir(current["wind_direction_10m"]),
        "is_day": bool(current["is_day"]),
        "description": label,
        "icon": icon,
        "updated": datetime.fromisoformat(current["time"]).strftime("%d.%m.%Y %H:%M"),
    }

    daily = data["daily"]
    forecast = []
    for i, date_str in enumerate(daily["time"]):
        date = datetime.fromisoformat(date_str)
        d_label, d_icon = describe(daily["weather_code"][i])
        forecast.append({
            "weekday": WEEKDAYS[date.weekday()],
            "date": date.strftime("%d.%m"),
            "t_max": round(daily["temperature_2m_max"][i]),
            "t_min": round(daily["temperature_2m_min"][i]),
            "precipitation": daily["precipitation_sum"][i],
            "description": d_label,
            "icon": d_icon,
        })

    hourly = data["hourly"]
    current_hour = datetime.fromisoformat(current["time"]).replace(minute=0, second=0, microsecond=0)
    hours = []
    for i, t in enumerate(hourly["time"]):
        hour = datetime.fromisoformat(t)
        if hour < current_hour:
            continue
        h_label, h_icon = describe(hourly["weather_code"][i])
        hours.append({
            "time": hour.strftime("%H:%M"),
            "temperature": round(hourly["temperature_2m"][i]),
            "precipitation_probability": hourly["precipitation_probability"][i],
            "icon": h_icon,
            "description": h_label,
        })
        if len(hours) >= 24:
            break

    sunrise = datetime.fromisoformat(daily["sunrise"][0]).strftime("%H:%M")
    sunset = datetime.fromisoformat(daily["sunset"][0]).strftime("%H:%M")

    return {
        "now": now,
        "forecast": forecast,
        "hours": hours,
        "sunrise": sunrise,
        "sunset": sunset,
    }


@app.route("/")
def index():
    error = None
    view = None
    try:
        view = build_view(fetch_weather())
    except Exception as exc:
        error = f"Не удалось получить данные о погоде: {exc}"
    return render_template("index.html", view=view, error=error)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

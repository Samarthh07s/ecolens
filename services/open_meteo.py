"""
Open-Meteo client: geocoding, weather and air quality.

- Every call has an 8 s timeout and 2 retries (3 attempts in total).
- The last good combined response per location is cached in SQLite so the
  dashboard keeps working (with an "Offline" badge) when the internet drops.
"""
import time
from datetime import datetime, timedelta, timezone

import requests

import config
import database as db


class ApiError(Exception):
    """Raised when the upstream API cannot be reached or returns bad data."""


def location_key(lat: float, lon: float) -> str:
    # ~1 km grid so that tiny GPS jitter maps to the same saved location
    return f"{lat:.2f},{lon:.2f}"


# ---------------------------------------------------------------------------
# HTTP with timeout + retry
# ---------------------------------------------------------------------------
def _get_json(url: str, params: dict) -> dict:
    last_error = None
    for attempt in range(config.HTTP_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=config.HTTP_TIMEOUT_SECONDS)
            if 500 <= resp.status_code < 600:
                raise ApiError(f"Server error {resp.status_code}")
            if resp.status_code != 200:
                # 4xx: our request is wrong, retrying will not help
                raise ApiError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            if isinstance(data, dict) and data.get("error"):
                raise ApiError(str(data.get("reason", "API error")))
            return data
        except ApiError as e:
            last_error = e
            if "HTTP 4" in str(e):
                break
        except (requests.Timeout, requests.ConnectionError, ValueError) as e:
            last_error = e
        if attempt < config.HTTP_RETRIES:
            time.sleep(config.HTTP_BACKOFF_SECONDS * (attempt + 1))
    raise ApiError(f"Could not reach {url.split('/')[2]}: {last_error}")


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------
def search_cities(query: str, count: int = 8) -> list:
    data = _get_json(config.GEOCODING_URL, {
        "name": query, "count": count, "language": "en", "format": "json",
    })
    out = []
    for r in data.get("results") or []:
        parts = [r.get("name"), r.get("admin1"), r.get("country")]
        label = ", ".join(p for p in dict.fromkeys(parts) if p)
        out.append({
            "name": label,
            "lat": round(float(r["latitude"]), 4),
            "lon": round(float(r["longitude"]), 4),
            "country_code": r.get("country_code", ""),
            "population": r.get("population"),
        })
    return out


# ---------------------------------------------------------------------------
# Weather + air quality
# ---------------------------------------------------------------------------
WEATHER_VARS = "temperature_2m,relative_humidity_2m,apparent_temperature,uv_index,wind_speed_10m"
AIR_VARS = "us_aqi,pm2_5,pm10"


def _fetch_raw(lat: float, lon: float):
    common = {
        "latitude": lat, "longitude": lon, "timezone": "auto",
        "past_days": config.PAST_DAYS, "forecast_days": config.FORECAST_DAYS,
    }
    weather = _get_json(config.WEATHER_URL, {
        **common,
        "current": WEATHER_VARS + ",weather_code,is_day",
        "hourly": WEATHER_VARS,
    })
    air = _get_json(config.AIR_QUALITY_URL, {
        **common,
        "current": AIR_VARS,
        "hourly": AIR_VARS,
    })
    return weather, air


def _num(v):
    try:
        if v is None:
            return None
        f = float(v)
        return None if f != f else round(f, 2)   # NaN -> None
    except (TypeError, ValueError):
        return None


def normalise(weather: dict, air: dict) -> dict:
    """Merge the two Open-Meteo responses into one simple structure."""
    if "current" not in weather or "hourly" not in weather:
        raise ApiError("Weather response is missing data")
    offset = int(weather.get("utc_offset_seconds", 0))

    wc, wh = weather["current"], weather["hourly"]
    ac, ah = air.get("current", {}) or {}, air.get("hourly", {}) or {}

    # Index air-quality hourly rows by local time string for merging
    air_by_time = {}
    for i, t in enumerate(ah.get("time", [])):
        air_by_time[t] = {
            "aqi": _num(ah.get("us_aqi", [None])[i] if i < len(ah.get("us_aqi", [])) else None),
            "pm25": _num(ah.get("pm2_5", [None])[i] if i < len(ah.get("pm2_5", [])) else None),
            "pm10": _num(ah.get("pm10", [None])[i] if i < len(ah.get("pm10", [])) else None),
        }

    def col(name, i):
        arr = wh.get(name) or []
        return _num(arr[i]) if i < len(arr) else None

    hourly = []
    for i, t in enumerate(wh.get("time", [])):
        local = datetime.strptime(t, "%Y-%m-%dT%H:%M")
        utc = (local - timedelta(seconds=offset)).replace(tzinfo=timezone.utc)
        a = air_by_time.get(t, {})
        hourly.append({
            "time_local": t,
            "ts": db.iso(utc),
            "temperature": col("temperature_2m", i),
            "feels_like": col("apparent_temperature", i),
            "humidity": col("relative_humidity_2m", i),
            "uv": col("uv_index", i),
            "wind": col("wind_speed_10m", i),
            "aqi": a.get("aqi"),
            "pm25": a.get("pm25"),
            "pm10": a.get("pm10"),
        })

    current = {
        "time_local": wc.get("time"),
        "temperature": _num(wc.get("temperature_2m")),
        "feels_like": _num(wc.get("apparent_temperature")),
        "humidity": _num(wc.get("relative_humidity_2m")),
        "uv": _num(wc.get("uv_index")),
        "wind": _num(wc.get("wind_speed_10m")),
        "weather_code": wc.get("weather_code"),
        "is_day": wc.get("is_day"),
        "aqi": _num(ac.get("us_aqi")),
        "pm25": _num(ac.get("pm2_5")),
        "pm10": _num(ac.get("pm10")),
    }

    # Fill any gaps in "current" from the matching hourly row
    hour_key = (current["time_local"] or "")[:13] + ":00"
    match = next((h for h in hourly if h["time_local"] == hour_key), None)
    if match:
        for k in ("temperature", "feels_like", "humidity", "uv", "wind", "aqi", "pm25", "pm10"):
            if current.get(k) is None:
                current[k] = match.get(k)

    if current["temperature"] is None:
        raise ApiError("Weather response has no temperature")

    return {
        "timezone": weather.get("timezone", "UTC"),
        "timezone_abbr": weather.get("timezone_abbreviation", ""),
        "utc_offset_seconds": offset,
        "current": current,
        "hourly": hourly,
    }


def get_environment(lat: float, lon: float) -> dict:
    """Live data with SQLite fallback.

    Returns {"data": <normalised>, "offline": bool, "fetched_at": iso, "error": str|None}
    Raises ApiError only if the network fails AND nothing is cached.
    """
    key = location_key(lat, lon)
    try:
        weather, air = _fetch_raw(lat, lon)
        data = normalise(weather, air)
        db.save_cache(key, data)
        return {"data": data, "offline": False, "fetched_at": db.iso(db.utc_now()), "error": None}
    except ApiError as e:
        cached = db.load_cache(key)
        if cached:
            return {"data": cached["payload"], "offline": True,
                    "fetched_at": cached["fetched_at"], "error": str(e)}
        raise

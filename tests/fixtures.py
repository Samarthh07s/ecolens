"""
Realistic, deterministic Open-Meteo-shaped responses for tests.
(Used ONLY by the test suite - the real app never shows fake data.)
"""
import math
from datetime import datetime, timedelta, timezone

IST_OFFSET = 19800  # +05:30


def _hours(now_utc, past_days=2, forecast_days=2, offset=IST_OFFSET):
    local_now = now_utc + timedelta(seconds=offset)
    start = (local_now - timedelta(days=past_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    n = 24 * (past_days + forecast_days)
    return [start + timedelta(hours=i) for i in range(n)]


def weather_response(now_utc=None, temp_base=27.0, rh_base=55.0, uv_peak=8.0, wind=6.0):
    now_utc = now_utc or datetime.now(timezone.utc)
    hours = _hours(now_utc)
    temps, rhs, apps, uvs, winds = [], [], [], [], []
    for h in hours:
        phase = math.sin((h.hour - 9) / 24 * 2 * math.pi)
        t = temp_base + 5 * phase
        rh = rh_base - 15 * phase
        uv = max(0.0, uv_peak * math.sin((h.hour - 6) / 12 * math.pi)) if 6 <= h.hour <= 18 else 0.0
        temps.append(round(t, 1)); rhs.append(round(rh)); apps.append(round(t + 1.5, 1))
        uvs.append(round(uv, 2)); winds.append(wind)
    local_now = now_utc + timedelta(seconds=IST_OFFSET)
    cur_t = local_now.replace(minute=(local_now.minute // 15) * 15, second=0, microsecond=0)
    idx = next(i for i, h in enumerate(hours) if h.strftime("%Y-%m-%dT%H") == cur_t.strftime("%Y-%m-%dT%H"))
    return {
        "latitude": 18.5, "longitude": 73.875, "utc_offset_seconds": IST_OFFSET,
        "timezone": "Asia/Kolkata", "timezone_abbreviation": "GMT+5:30",
        "current": {
            "time": cur_t.strftime("%Y-%m-%dT%H:%M"), "interval": 900,
            "temperature_2m": temps[idx], "relative_humidity_2m": rhs[idx],
            "apparent_temperature": apps[idx], "uv_index": uvs[idx],
            "wind_speed_10m": winds[idx], "weather_code": 1, "is_day": 1,
        },
        "hourly": {
            "time": [h.strftime("%Y-%m-%dT%H:%M") for h in hours],
            "temperature_2m": temps, "relative_humidity_2m": rhs,
            "apparent_temperature": apps, "uv_index": uvs, "wind_speed_10m": winds,
        },
    }


def air_response(now_utc=None, aqi_base=95.0):
    now_utc = now_utc or datetime.now(timezone.utc)
    hours = _hours(now_utc)
    aqis, pm25, pm10 = [], [], []
    for h in hours:
        a = aqi_base + 30 * math.cos((h.hour - 8) / 24 * 2 * math.pi)
        aqis.append(round(a)); pm25.append(round(a * 0.35, 1)); pm10.append(round(a * 0.7, 1))
    local_now = now_utc + timedelta(seconds=IST_OFFSET)
    idx = next(i for i, h in enumerate(hours) if h.strftime("%Y-%m-%dT%H") == local_now.strftime("%Y-%m-%dT%H"))
    return {
        "latitude": 18.5, "longitude": 73.875, "utc_offset_seconds": IST_OFFSET,
        "current": {"time": local_now.strftime("%Y-%m-%dT%H:00"), "us_aqi": aqis[idx],
                    "pm2_5": pm25[idx], "pm10": pm10[idx]},
        "hourly": {"time": [h.strftime("%Y-%m-%dT%H:%M") for h in hours],
                   "us_aqi": aqis, "pm2_5": pm25, "pm10": pm10},
    }


GEOCODE_PUNE = {
    "results": [
        {"name": "Pune", "latitude": 18.51957, "longitude": 73.85535, "country_code": "IN",
         "admin1": "Maharashtra", "country": "India", "population": 3124458},
        {"name": "Pune", "latitude": -8.5667, "longitude": 125.6, "country_code": "TL",
         "admin1": "Ermera", "country": "Timor Leste"},
    ]
}


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = str(payload)[:200]

    def json(self):
        return self._payload


def make_fake_get(aqi_base=95.0, temp_base=27.0, rh_base=55.0, uv_peak=8.0, wind=6.0, fail=False):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append((url, dict(params or {}), timeout))
        if fail:
            import requests
            raise requests.ConnectionError("network down")
        if "geocoding" in url:
            return FakeResponse(GEOCODE_PUNE)
        if "air-quality" in url:
            return FakeResponse(air_response(aqi_base=aqi_base))
        return FakeResponse(weather_response(temp_base=temp_base, rh_base=rh_base,
                                             uv_peak=uv_peak, wind=wind))
    fake_get.calls = calls
    return fake_get

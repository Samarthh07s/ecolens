from datetime import timedelta

import numpy as np
import pandas as pd

import database as db
from analysis import trends

LOC = {"key": "18.52,73.86", "name": "Pune", "lat": 18.52, "lon": 73.86}


def seed(values_aqi, values_temp=None, source="hourly"):
    now = db.utc_now().replace(minute=0, second=0)
    rows = []
    n = len(values_aqi)
    for i, a in enumerate(values_aqi):
        ts = db.iso(now - timedelta(hours=n - 1 - i))
        t = values_temp[i] if values_temp else 25.0
        rows.append({"ts": ts, "aqi": a, "temperature": t, "humidity": 50, "uv": 0, "score": 100 - a / 3})
    db.save_hourly_readings(LOC, rows)


def test_empty_history():
    out = trends.summarize(LOC["key"], "24h")
    assert out["empty"] is True


def test_rising_aqi_is_worsening():
    seed(list(range(50, 74)))                       # +1 AQI per hour
    out = trends.summarize(LOC["key"], "24h")
    assert out["trends"]["aqi"]["direction"] == "worsening"
    assert out["trends"]["aqi"]["slope_per_hour"] > 0.9
    assert out["trends"]["score"]["direction"] == "worsening"


def test_falling_aqi_is_improving_and_flat_is_stable():
    assert trends.trend_direction(np.arange(120, 96, -1), "aqi")["direction"] == "improving"
    assert trends.trend_direction(np.full(24, 80.0), "aqi")["direction"] == "stable"
    assert trends.trend_direction(np.arange(20, 44), "temperature")["direction"] == "rising"


def test_stats_and_moving_average():
    seed([10, 20, 30, 40, 50, 60])
    out = trends.summarize(LOC["key"], "24h")
    assert out["stats"]["aqi"] == {"avg": 35.0, "min": 10.0, "max": 60.0}
    ma = out["series"]["aqi"]["moving_avg"]
    assert ma[2] == 20.0                            # mean(10,20,30), window 3


def test_linear_forecast_extends_trend():
    idx = pd.date_range("2026-10-24 00:00", periods=12, freq="1h", tz="UTC")
    s = pd.Series(np.arange(12, dtype=float) * 2 + 100, index=idx)
    f = trends.linear_forecast(s, hours=6)
    assert len(f) == 6
    assert f[0]["value"] == 124.0 and f[-1]["value"] == 134.0


def test_forecast_never_negative_aqi():
    idx = pd.date_range("2026-10-24 00:00", periods=8, freq="1h", tz="UTC")
    s = pd.Series([40, 30, 20, 10, 5, 3, 2, 1], index=idx, dtype=float)
    assert all(p["value"] >= 0 for p in trends.linear_forecast(s, floor=0))


def test_range_filter_excludes_old_rows():
    now = db.utc_now()
    db.save_reading(LOC, db.iso(now - timedelta(days=3)), "live", {"aqi": 999, "temperature": 20})
    seed([50, 51, 52, 53])
    assert trends.summarize(LOC["key"], "24h")["stats"]["aqi"]["max"] == 53
    assert trends.summarize(LOC["key"], "7d")["stats"]["aqi"]["max"] == 999


def test_export_frame_columns():
    seed([50, 60])
    df = trends.export_frame(LOC["key"], "24h")
    assert list(df.columns[:5]) == ["timestamp_utc", "location", "lat", "lon", "source"]
    assert len(df) == 2

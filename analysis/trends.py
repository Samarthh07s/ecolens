"""
History & trends with Pandas + NumPy.

- Resamples readings to hourly means (live refreshes and API hourly data
  are combined; when both exist for an hour, they are averaged).
- Moving-average overlay, avg/min/max summary.
- Trend direction from the slope of a NumPy linear fit (np.polyfit).
- A simple next-6-hours *estimate* using linear regression on the most
  recent hourly points. This is deliberately simple and labelled as such.
"""
from datetime import timedelta

import numpy as np
import pandas as pd

import database as db

RANGES = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
METRICS = ["aqi", "temperature", "score", "pm25", "humidity", "uv"]

# For each metric: is a rising value good or bad?
HIGHER_IS_BETTER = {"aqi": False, "score": True, "pm25": False}


def load_frame(location_key=None, range_key="24h", now=None) -> pd.DataFrame:
    now = now or db.utc_now()
    since = db.iso(now - RANGES.get(range_key, RANGES["24h"]))
    rows = db.fetch_readings(location_key, since)
    # Only past data - never forecast hours
    rows = [r for r in rows if r["ts"] <= db.iso(now)]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df


def hourly_series(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    cols = [c for c in METRICS if c in df]
    hourly = (df.set_index("ts")[cols].apply(pd.to_numeric, errors="coerce")
              .resample("1h").mean().dropna(how="all"))
    return hourly


def trend_direction(values, metric: str, per_hours: float = 1.0) -> dict:
    """Classify a series as improving / stable / worsening from the
    slope of a least-squares line (np.polyfit, degree 1)."""
    y = np.asarray(values, dtype=float)
    x = np.arange(len(y), dtype=float) * per_hours
    mask = ~np.isnan(y)
    x, y = x[mask], y[mask]
    if len(y) < 3:
        return {"direction": "insufficient data", "slope_per_hour": None, "change_24h": None}
    slope, _ = np.polyfit(x, y, 1)
    change_24h = slope * 24
    scale = max(abs(float(np.nanmean(y))), 1.0)
    # "Stable" if the fitted change over 24 h is under 5% of the mean (min 1 unit)
    threshold = max(0.05 * scale, 1.0)
    if abs(change_24h) < threshold:
        direction = "stable"
    elif metric in HIGHER_IS_BETTER:
        rising_good = HIGHER_IS_BETTER[metric]
        direction = "improving" if (change_24h > 0) == rising_good else "worsening"
    else:
        direction = "rising" if change_24h > 0 else "falling"
    return {"direction": direction, "slope_per_hour": round(float(slope), 3),
            "change_24h": round(float(change_24h), 2)}


def linear_forecast(series: pd.Series, hours: int = 6, lookback: int = 12, floor=None) -> list:
    s = series.dropna().tail(lookback)
    if len(s) < 4:
        return []
    t0 = s.index[0]
    x = np.array([(t - t0).total_seconds() / 3600 for t in s.index])
    slope, intercept = np.polyfit(x, s.values.astype(float), 1)
    last = s.index[-1]
    out = []
    for h in range(1, hours + 1):
        t = last + pd.Timedelta(hours=h)
        xv = (t - t0).total_seconds() / 3600
        v = slope * xv + intercept
        if floor is not None:
            v = max(floor, v)
        out.append({"ts": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "value": round(float(v), 1)})
    return out


def moving_average(series: pd.Series, window: int) -> list:
    ma = series.rolling(window, min_periods=1).mean()
    return [None if pd.isna(v) else round(float(v), 1) for v in ma]


def summarize(location_key=None, range_key="24h", now=None) -> dict:
    df = load_frame(location_key, range_key, now)
    if df.empty:
        return {"empty": True, "range": range_key, "points": 0}

    hourly = hourly_series(df)
    if hourly.empty:
        return {"empty": True, "range": range_key, "points": 0}

    ma_window = {"24h": 3, "7d": 6, "30d": 24}.get(range_key, 3)
    labels = [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in hourly.index]

    series, stats, trends = {}, {}, {}
    for m in ["aqi", "temperature", "score"]:
        if m not in hourly:
            continue
        s = hourly[m]
        series[m] = {
            "values": [None if pd.isna(v) else round(float(v), 1) for v in s],
            "moving_avg": moving_average(s, ma_window),
        }
        valid = s.dropna()
        stats[m] = {
            "avg": round(float(valid.mean()), 1) if len(valid) else None,
            "min": round(float(valid.min()), 1) if len(valid) else None,
            "max": round(float(valid.max()), 1) if len(valid) else None,
        }
        trends[m] = trend_direction(s.values, m)

    forecast = {
        "aqi": linear_forecast(hourly["aqi"], floor=0) if "aqi" in hourly else [],
        "temperature": linear_forecast(hourly["temperature"]) if "temperature" in hourly else [],
    }
    sources = df["source"].value_counts().to_dict()

    return {
        "empty": False,
        "range": range_key,
        "points": int(len(hourly)),
        "raw_points": int(len(df)),
        "sources": {k: int(v) for k, v in sources.items()},
        "moving_average_window": ma_window,
        "labels": labels,
        "series": series,
        "stats": stats,
        "trends": trends,
        "overall": trends.get("score", {}).get("direction", "insufficient data"),
        "forecast": forecast,
    }


def export_frame(location_key=None, range_key="30d") -> pd.DataFrame:
    df = load_frame(location_key, range_key)
    if df.empty:
        return pd.DataFrame(columns=["timestamp_utc", "location", "source"] + db.READING_FIELDS)
    df = df.sort_values("ts")
    df["timestamp_utc"] = df["ts"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df = df.rename(columns={"location_name": "location"})
    return df[["timestamp_utc", "location", "lat", "lon", "source"] + db.READING_FIELDS]

"""
SQLite persistence for EcoLens.

All SQL uses parameter placeholders (?) - never string formatting - so
user input can never change the meaning of a query.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    location_key  TEXT    NOT NULL,
    location_name TEXT    NOT NULL,
    lat           REAL    NOT NULL,
    lon           REAL    NOT NULL,
    ts            TEXT    NOT NULL,          -- ISO-8601 UTC, e.g. 2026-10-24T10:00:00Z
    source        TEXT    NOT NULL,          -- 'live' (dashboard refresh) or 'hourly' (API past data)
    aqi           REAL,
    pm25          REAL,
    pm10          REAL,
    temperature   REAL,
    feels_like    REAL,
    humidity      REAL,
    uv            REAL,
    wind          REAL,
    heat_index    REAL,
    noise         REAL,
    score         REAL,
    UNIQUE (location_key, ts, source)
);
CREATE INDEX IF NOT EXISTS idx_readings_loc_ts ON readings (location_key, ts);

CREATE TABLE IF NOT EXISTS alerts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    location_key  TEXT NOT NULL,
    location_name TEXT NOT NULL,
    kind          TEXT NOT NULL,
    severity      TEXT NOT NULL,
    title         TEXT NOT NULL,
    action        TEXT NOT NULL,
    value         REAL,
    hour_bucket   TEXT NOT NULL,             -- YYYY-MM-DDTHH (UTC) for de-duplication
    created_at    TEXT NOT NULL,
    UNIQUE (location_key, kind, hour_bucket)
);

CREATE TABLE IF NOT EXISTS api_cache (
    location_key  TEXT PRIMARY KEY,
    payload       TEXT NOT NULL,
    fetched_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS noise_readings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    location_key  TEXT NOT NULL,
    db            REAL NOT NULL,
    method        TEXT NOT NULL,             -- 'mic' or 'manual'
    ts            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id        TEXT PRIMARY KEY,
    display_name      TEXT NOT NULL DEFAULT 'Eco explorer',
    health_profile    TEXT NOT NULL DEFAULT 'general',
    units             TEXT NOT NULL DEFAULT 'metric',
    favorite_locations TEXT NOT NULL DEFAULT '[]',
    updated_at        TEXT NOT NULL
);
"""

READING_FIELDS = [
    "aqi", "pm25", "pm10", "temperature", "feels_like", "humidity",
    "uv", "wind", "heat_index", "noise", "score",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


@contextmanager
def connect():
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Readings
# ---------------------------------------------------------------------------
def save_reading(location: dict, ts: str, source: str, values: dict) -> int:
    cols = ["location_key", "location_name", "lat", "lon", "ts", "source"] + READING_FIELDS
    params = [location["key"], location["name"], location["lat"], location["lon"], ts, source]
    params += [values.get(f) for f in READING_FIELDS]
    placeholders = ",".join("?" for _ in cols)
    sql = f"INSERT OR IGNORE INTO readings ({','.join(cols)}) VALUES ({placeholders})"
    with connect() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def save_hourly_readings(location: dict, rows: list) -> int:
    """Bulk-insert past hourly rows from the API (duplicates are ignored)."""
    if not rows:
        return 0
    cols = ["location_key", "location_name", "lat", "lon", "ts", "source"] + READING_FIELDS
    sql = (f"INSERT OR IGNORE INTO readings ({','.join(cols)}) "
           f"VALUES ({','.join('?' for _ in cols)})")
    data = [
        [location["key"], location["name"], location["lat"], location["lon"], r["ts"], "hourly"]
        + [r.get(f) for f in READING_FIELDS]
        for r in rows
    ]
    with connect() as conn:
        before = conn.total_changes
        conn.executemany(sql, data)
        return conn.total_changes - before


def update_latest_live_noise(location_key: str, noise_db: float, score: float, within_minutes=60) -> bool:
    """Attach a noise measurement to the most recent live reading for a location."""
    since = iso(utc_now().replace(second=0) - _minutes(within_minutes))
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM readings WHERE location_key = ? AND source = 'live' AND ts >= ? "
            "ORDER BY ts DESC LIMIT 1",
            (location_key, since),
        ).fetchone()
        if not row:
            return False
        conn.execute("UPDATE readings SET noise = ?, score = ? WHERE id = ?",
                     (noise_db, score, row["id"]))
        return True


def fetch_readings(location_key=None, since_iso=None) -> list:
    sql = "SELECT * FROM readings WHERE 1=1"
    params = []
    if location_key:
        sql += " AND location_key = ?"
        params.append(location_key)
    if since_iso:
        sql += " AND ts >= ?"
        params.append(since_iso)
    sql += " ORDER BY ts ASC"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def list_locations() -> list:
    with connect() as conn:
        rows = conn.execute(
            "SELECT location_key, MAX(location_name) AS location_name, COUNT(*) AS n, "
            "MAX(ts) AS last_ts FROM readings GROUP BY location_key ORDER BY last_ts DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Noise
# ---------------------------------------------------------------------------
def save_noise(location_key: str, db_value: float, method: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO noise_readings (location_key, db, method, ts) VALUES (?, ?, ?, ?)",
            (location_key, db_value, method, iso(utc_now())),
        )


def latest_noise(location_key: str, within_minutes=60):
    since = iso(utc_now() - _minutes(within_minutes))
    with connect() as conn:
        row = conn.execute(
            "SELECT db, method, ts FROM noise_readings WHERE location_key = ? AND ts >= ? "
            "ORDER BY ts DESC, id DESC LIMIT 1",
            (location_key, since),
        ).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
def save_alerts(location: dict, alerts: list) -> list:
    """Insert alerts, de-duplicated per location + kind + UTC hour.
    Returns the alerts with an `is_new` flag so the UI can notify only once."""
    now = utc_now()
    bucket = now.strftime("%Y-%m-%dT%H")
    out = []
    with connect() as conn:
        for a in alerts:
            cur = conn.execute(
                "INSERT OR IGNORE INTO alerts (location_key, location_name, kind, severity, "
                "title, action, value, hour_bucket, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (location["key"], location["name"], a["kind"], a["severity"], a["title"],
                 a["action"], a.get("value"), bucket, iso(now)),
            )
            out.append({**a, "is_new": cur.rowcount == 1})
    return out


def list_alerts(limit=200) -> list:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def clear_alerts() -> int:
    with connect() as conn:
        cur = conn.execute("DELETE FROM alerts")
        return cur.rowcount


# ---------------------------------------------------------------------------
# Local/demo personalization
# ---------------------------------------------------------------------------
def get_user_profile(profile_id="demo"):
    with connect() as conn:
        row = conn.execute(
            "SELECT profile_id, display_name, health_profile, units, favorite_locations, updated_at "
            "FROM user_profiles WHERE profile_id = ?", (profile_id,)
        ).fetchone()
        if not row:
            return {
                "profile_id": profile_id,
                "display_name": "Eco explorer",
                "health_profile": "general",
                "units": "metric",
                "favorite_locations": [],
                "updated_at": None,
            }
        out = dict(row)
        try:
            out["favorite_locations"] = json.loads(out["favorite_locations"])
        except (TypeError, ValueError):
            out["favorite_locations"] = []
        return out


def save_user_profile(profile_id, values):
    now = iso(utc_now())
    favorites = values.get("favorite_locations") or []
    with connect() as conn:
        conn.execute(
            "INSERT INTO user_profiles "
            "(profile_id, display_name, health_profile, units, favorite_locations, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(profile_id) DO UPDATE SET display_name=excluded.display_name, "
            "health_profile=excluded.health_profile, units=excluded.units, "
            "favorite_locations=excluded.favorite_locations, updated_at=excluded.updated_at",
            (
                profile_id,
                values.get("display_name", "Eco explorer"),
                values.get("health_profile", "general"),
                values.get("units", "metric"),
                json.dumps(favorites),
                now,
            ),
        )
    return get_user_profile(profile_id)


# ---------------------------------------------------------------------------
# API response cache (for offline mode)
# ---------------------------------------------------------------------------
def save_cache(location_key: str, payload: dict) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO api_cache (location_key, payload, fetched_at) VALUES (?, ?, ?) "
            "ON CONFLICT(location_key) DO UPDATE SET payload = excluded.payload, "
            "fetched_at = excluded.fetched_at",
            (location_key, json.dumps(payload), iso(utc_now())),
        )


def load_cache(location_key: str):
    with connect() as conn:
        row = conn.execute(
            "SELECT payload, fetched_at FROM api_cache WHERE location_key = ?", (location_key,)
        ).fetchone()
        if not row:
            return None
        return {"payload": json.loads(row["payload"]), "fetched_at": row["fetched_at"]}


def _minutes(n):
    from datetime import timedelta
    return timedelta(minutes=n)

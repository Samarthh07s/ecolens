"""
EcoLens - AI Environmental Analyzer
Flask routes (pages) + JSON API.

Run:  python app.py    then open http://127.0.0.1:5000
"""
import io
import math
import re
import threading
import webbrowser

from flask import Flask, Response, jsonify, render_template, request

import config
import database as db
from analysis import analyzer, recommender, trends
from services import open_meteo as om

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

PROFILE_NAMES = set(recommender.PROFILES)
PROFILE_ID = "demo"


# ---------------------------------------------------------------------------
# Helpers: validation
# ---------------------------------------------------------------------------
class BadRequest(Exception):
    pass


def _float_arg(value, name, lo, hi):
    try:
        f = float(value)
    except (TypeError, ValueError):
        raise BadRequest(f"'{name}' must be a number")
    if not math.isfinite(f) or not (lo <= f <= hi):
        raise BadRequest(f"'{name}' must be between {lo} and {hi}")
    return f


def _clean_text(value, max_len=100):
    value = (value or "").strip()
    value = re.sub(r"[\x00-\x1f\x7f]", "", value)      # strip control characters
    value = re.sub(r"\s+", " ", value)
    return value[:max_len]


def _profile(value):
    value = (value or "").strip().lower()
    return value if value in PROFILE_NAMES else recommender.DEFAULT_PROFILE


def _range(value):
    return value if value in trends.RANGES else "24h"


def _location_from(args):
    lat = _float_arg(args.get("lat", config.DEFAULT_LOCATION["lat"]), "lat", -90, 90)
    lon = _float_arg(args.get("lon", config.DEFAULT_LOCATION["lon"]), "lon", -180, 180)
    name = _clean_text(args.get("name")) or (
        config.DEFAULT_LOCATION["name"] if "lat" not in args else f"{lat:.3f}, {lon:.3f}")
    return {"name": name, "lat": round(lat, 4), "lon": round(lon, 4), "key": om.location_key(lat, lon)}


def _location_key_arg(value):
    value = (value or "").strip()
    if not value:
        return None
    if not re.fullmatch(r"-?\d{1,2}\.\d{2},-?\d{1,3}\.\d{2}", value):
        raise BadRequest("Invalid location filter")
    return value


def _profile_id(value):
    value = _clean_text(value, 40)
    return value or PROFILE_ID


def _profile_payload(body):
    profile = _profile(body.get("health_profile"))
    name = _clean_text(body.get("display_name"), 60) or "Eco explorer"
    units = body.get("units") if body.get("units") in ("metric", "imperial") else "metric"
    favorites = body.get("favorite_locations") or []
    if not isinstance(favorites, list):
        raise BadRequest("'favorite_locations' must be a list")
    clean_favorites = []
    for item in favorites[:8]:
        if not isinstance(item, dict):
            continue
        try:
            lat = _float_arg(item.get("lat"), "favorite latitude", -90, 90)
            lon = _float_arg(item.get("lon"), "favorite longitude", -180, 180)
        except BadRequest:
            continue
        clean_favorites.append({
            "name": _clean_text(item.get("name"), 100) or f"{lat:.3f}, {lon:.3f}",
            "lat": round(lat, 4), "lon": round(lon, 4),
        })
    return {"display_name": name, "health_profile": profile, "units": units,
            "favorite_locations": clean_favorites}


@app.errorhandler(BadRequest)
def _bad_request(e):
    return jsonify({"error": str(e)}), 400


@app.after_request
def _security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'"
    )
    return resp


# ---------------------------------------------------------------------------
# Core: turn raw API data into the dashboard payload
# ---------------------------------------------------------------------------
def build_payload(env: dict, location: dict, profile: str, save: bool) -> dict:
    data = env["data"]
    cur = dict(data["current"])

    noise = db.latest_noise(location["key"])
    cur["noise"] = noise["db"] if noise else None

    result = analyzer.analyze(cur)
    reading = result["reading"]
    score = result["score"]

    rec = recommender.recommend(reading, profile)
    best = recommender.best_time_window(data["hourly"], cur.get("time_local"))

    alerts = recommender.alerts_for(reading, profile)
    alerts = db.save_alerts(location, alerts) if alerts else []

    if save:
        values = {k: reading.get(k) for k in db.READING_FIELDS}
        values["score"] = score["score"]
        db.save_reading(location, db.iso(db.utc_now()), "live", values)
        _save_past_hourly(location, data["hourly"])

    # Next 24 hours for a small outlook strip
    now_hour = (cur.get("time_local") or "")[:13]
    upcoming = [h for h in data["hourly"] if h["time_local"][:13] >= now_hour][:24]
    today = now_hour[:10]
    uv_today = [h["uv"] for h in data["hourly"] if h["time_local"][:10] == today and h["uv"] is not None]
    reading["uv_max_today"] = max(uv_today) if uv_today else None

    return {
        "location": location,
        "timezone": data.get("timezone"),
        "current": reading,
        "noise_meta": noise,
        "bands": result["bands"],
        "analysis": {"score": score, "patterns": result["patterns"]},
        "recommendations": {**rec, "best_window": best},
        "alerts": alerts,
        "upcoming": upcoming,
        "updated_at": env["fetched_at"],
        "offline": env["offline"],
        "offline_reason": env.get("error"),
    }


def _save_past_hourly(location, hourly):
    now_iso = db.iso(db.utc_now())
    rows = []
    for h in hourly:
        if h["ts"] > now_iso:
            continue            # forecast hours are never stored as history
        enriched = analyzer.enrich(h)
        rows.append({**{k: enriched.get(k) for k in db.READING_FIELDS},
                     "ts": h["ts"], "score": analyzer.health_score(enriched)["score"]})
    db.save_hourly_readings(location, rows)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.context_processor
def _globals():
    return {"APP_NAME": config.APP_NAME, "APP_TAGLINE": config.APP_TAGLINE}


@app.route("/")
def dashboard():
    return render_template("dashboard.html", active="dashboard",
                           default=config.DEFAULT_LOCATION,
                           profiles=recommender.PROFILES,
                           method=analyzer.methodology())


@app.route("/trends")
def trends_page():
    return render_template("trends.html", active="trends")


@app.route("/alerts")
def alerts_page():
    return render_template("alerts.html", active="alerts")


@app.route("/about")
def about_page():
    return render_template("about.html", active="about", about=config.ABOUT,
                           weights=config.SCORE_WEIGHTS)


@app.route("/compare")
def compare_page():
    return render_template("compare.html", active="compare")


@app.route("/settings")
def settings_page():
    return render_template("settings.html", active="settings",
                           profiles=recommender.PROFILES)


@app.route("/report")
def report_page():
    location = _location_from(request.args)
    profile = _profile(request.args.get("profile"))
    try:
        env = om.get_environment(location["lat"], location["lon"])
    except om.ApiError:
        return render_template("report.html", error="Live data is unavailable for this location.",
                               location=location, payload=None), 503
    return render_template("report.html", location=location,
                           payload=build_payload(env, location, profile, save=False), error=None)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.get("/api/search")
def api_search():
    q = _clean_text(request.args.get("q"), 80)
    if len(q) < 2:
        return jsonify({"results": []})
    try:
        return jsonify({"results": om.search_cities(q)})
    except om.ApiError:
        return jsonify({"results": [], "error": "City search is unavailable (are you offline?)"}), 503


@app.get("/api/current")
def api_current():
    location = _location_from(request.args)
    profile = _profile(request.args.get("profile"))
    try:
        env = om.get_environment(location["lat"], location["lon"])
    except om.ApiError:
        return jsonify({"error": "Could not reach the weather service and no cached data exists "
                                 "for this location yet. Check your internet connection and retry."}), 503
    return jsonify(build_payload(env, location, profile, save=not env["offline"]))


@app.post("/api/noise")
def api_noise():
    body = request.get_json(silent=True) or {}
    location = _location_from({k: body.get(k) for k in ("lat", "lon", "name") if body.get(k) is not None})
    value = _float_arg(body.get("db"), "db", 0, 140)
    method = body.get("method") if body.get("method") in ("mic", "manual") else "manual"
    profile = _profile(body.get("profile"))
    db.save_noise(location["key"], round(value, 1), method)

    cached = db.load_cache(location["key"])
    if not cached:
        return jsonify({"saved": True, "db": round(value, 1), "payload": None})
    env = {"data": cached["payload"], "offline": False, "fetched_at": cached["fetched_at"], "error": None}
    payload = build_payload(env, location, profile, save=False)
    db.update_latest_live_noise(location["key"], round(value, 1), payload["analysis"]["score"]["score"])
    return jsonify({"saved": True, "db": round(value, 1), "payload": payload})


@app.get("/api/history")
def api_history():
    key = _location_key_arg(request.args.get("location"))
    rng = _range(request.args.get("range"))
    df = trends.load_frame(key, rng)
    rows = []
    if not df.empty:
        out = df.assign(ts=df["ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")).tail(1000)
        out = out.astype(object).where(out.notna(), None)      # NaN -> null (valid JSON)
        rows = out.to_dict(orient="records")
    return jsonify({"locations": db.list_locations(), "range": rng, "readings": rows})


@app.get("/api/trends")
def api_trends():
    key = _location_key_arg(request.args.get("location"))
    rng = _range(request.args.get("range"))
    return jsonify(trends.summarize(key, rng))


@app.get("/api/alerts")
def api_alerts():
    return jsonify({"alerts": db.list_alerts()})


@app.delete("/api/alerts")
def api_alerts_clear():
    return jsonify({"cleared": db.clear_alerts()})


@app.get("/api/methodology")
def api_methodology():
    return jsonify(analyzer.methodology())


@app.route("/api/profile", methods=["GET", "PUT"])
def api_profile():
    profile_id = _profile_id(request.args.get("id") or (request.get_json(silent=True) or {}).get("id"))
    if request.method == "GET":
        return jsonify(db.get_user_profile(profile_id))
    body = request.get_json(silent=True) or {}
    current = db.get_user_profile(profile_id)
    merged = {**current, **body}
    return jsonify(db.save_user_profile(profile_id, _profile_payload(merged)))


@app.get("/api/compare")
def api_compare():
    first = _location_from({
        "lat": request.args.get("lat1"), "lon": request.args.get("lon1"),
        "name": request.args.get("name1"),
    })
    second = _location_from({
        "lat": request.args.get("lat2"), "lon": request.args.get("lon2"),
        "name": request.args.get("name2"),
    })
    profile = _profile(request.args.get("profile"))
    items = []
    for location in (first, second):
        try:
            env = om.get_environment(location["lat"], location["lon"])
        except om.ApiError:
            return jsonify({"error": f"Could not load data for {location['name']}"}), 503
        items.append(build_payload(env, location, profile, save=False))
    return jsonify({"locations": items, "profile": profile})


@app.get("/api/export.csv")
def api_export():
    key = _location_key_arg(request.args.get("location"))
    rng = _range(request.args.get("range") or "30d")
    df = trends.export_frame(key, rng)
    # Prevent CSV/Excel formula injection from location names
    if "location" in df:
        df["location"] = df["location"].astype(str).map(
            lambda s: "'" + s if s[:1] in ("=", "+", "-", "@") else s)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=ecolens_history_{rng}.csv"})


db.init_db()

if __name__ == "__main__":
    print("=" * 60)
    print(f"  {config.APP_NAME} - {config.APP_TAGLINE}")
    print(f"  Database : {config.DB_PATH}")
    print(f"  Open     : http://{config.HOST}:{config.PORT}")
    print("  Stop     : press CTRL+C in this window")
    print("=" * 60)
    if getattr(config, "RUNTIME_DIR", config.BASE_DIR) != config.BASE_DIR:
        threading.Timer(
            1.2,
            lambda: webbrowser.open(f"http://{config.HOST}:{config.PORT}"),
        ).start()
    app.run(host=config.HOST, port=config.PORT, debug=False)

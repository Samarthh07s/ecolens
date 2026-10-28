"""
Personalised recommendations and alert rules.

Each profile has its own (tighter or looser) thresholds. The verdict is:
  Avoid             - any "unsafe" threshold crossed
  Take precautions  - any "caution" threshold crossed
  Safe              - otherwise
"""
import pandas as pd

import config
from analysis.analyzer import heat_index_c

PROFILES = {
    "general": {
        "label": "General", "aqi_caution": 100, "aqi_unsafe": 150, "aqi_alert": 150,
        "uv_caution": 6, "uv_unsafe": 11, "hi_caution": 32, "hi_unsafe": 41,
        "note": "Healthy adults.",
    },
    "children": {
        "label": "Children", "aqi_caution": 50, "aqi_unsafe": 100, "aqi_alert": 100,
        "uv_caution": 3, "uv_unsafe": 8, "hi_caution": 30, "hi_unsafe": 38,
        "note": "Children breathe faster and burn more easily.",
    },
    "elderly": {
        "label": "Elderly", "aqi_caution": 50, "aqi_unsafe": 100, "aqi_alert": 100,
        "uv_caution": 6, "uv_unsafe": 8, "hi_caution": 30, "hi_unsafe": 38,
        "note": "Older adults are more sensitive to heat and pollution.",
    },
    "asthma": {
        "label": "Asthma / Respiratory", "aqi_caution": 50, "aqi_unsafe": 100, "aqi_alert": 100,
        "uv_caution": 6, "uv_unsafe": 11, "hi_caution": 32, "hi_unsafe": 39,
        "note": "Fine particles can trigger attacks; keep reliever inhaler handy.",
    },
    "athlete": {
        "label": "Athlete", "aqi_caution": 75, "aqi_unsafe": 150, "aqi_alert": 150,
        "uv_caution": 6, "uv_unsafe": 11, "hi_caution": 29, "hi_unsafe": 35,
        "note": "Hard exercise multiplies how much air (and heat) you take in.",
    },
}
DEFAULT_PROFILE = "general"


def get_profile(name):
    return PROFILES.get(name, PROFILES[DEFAULT_PROFILE])


# ---------------------------------------------------------------------------
# Verdict + actions
# ---------------------------------------------------------------------------
def recommend(cur: dict, profile_name: str) -> dict:
    p = get_profile(profile_name)
    aqi, uv, hi = cur.get("aqi"), cur.get("uv"), cur.get("heat_index")
    hum, noise, pm25 = cur.get("humidity"), cur.get("noise"), cur.get("pm25")

    unsafe, caution = [], []
    if aqi is not None:
        if aqi > p["aqi_unsafe"]:
            unsafe.append(f"AQI {aqi:.0f} is above the {p['label']} limit of {p['aqi_unsafe']}.")
        elif aqi > p["aqi_caution"]:
            caution.append(f"AQI {aqi:.0f} is elevated for the {p['label']} profile.")
    if uv is not None:
        if uv >= p["uv_unsafe"]:
            unsafe.append(f"UV index {uv:.0f} is extreme for this profile.")
        elif uv >= p["uv_caution"]:
            caution.append(f"UV index {uv:.0f} - sun protection needed.")
    if hi is not None:
        if hi > p["hi_unsafe"]:
            unsafe.append(f"Heat index {hi:.0f}°C is dangerous for this profile.")
        elif hi > p["hi_caution"]:
            caution.append(f"Heat index {hi:.0f}°C - heat strain possible.")
    if noise is not None and noise > 80:
        caution.append(f"Noise around {noise:.0f} dB - limit exposure.")

    if unsafe:
        verdict, level = "Avoid", "avoid"
        summary = "Stay indoors or keep outdoor time short and light."
    elif caution:
        verdict, level = "Take precautions", "caution"
        summary = "Going out is fine with the precautions below."
    else:
        verdict, level = "Safe", "safe"
        summary = "Conditions are good for being outside."

    actions = []

    # Mask
    if aqi is not None and aqi > p["aqi_caution"]:
        actions.append({"icon": "mask", "title": "Wear an N95 mask",
                        "text": "A well-fitted N95/FFP2 filters fine particles (PM2.5). "
                                "Cloth and surgical masks do not."})
    else:
        actions.append({"icon": "mask", "title": "No mask needed",
                        "text": "Air quality is within this profile's comfort range."})

    # Exercise
    if unsafe:
        ex = ("Avoid outdoor exercise", "Move workouts indoors or reschedule to the best window below.")
    elif caution:
        ex = ("Light outdoor exercise only", "Prefer walks over runs; take breaks and watch for breathlessness.")
    else:
        ex = ("Great for outdoor exercise", "Conditions support running, cycling and sports.")
    actions.append({"icon": "run", "title": ex[0], "text": ex[1]})

    # Sunscreen
    if uv is None:
        pass
    elif uv < 3:
        actions.append({"icon": "sun", "title": "Sunscreen optional",
                        "text": "UV is low. SPF 15 is enough for long exposure."})
    elif uv < 6:
        actions.append({"icon": "sun", "title": "Use SPF 30",
                        "text": "Apply 15 minutes before going out; sunglasses recommended."})
    elif uv < 8:
        actions.append({"icon": "sun", "title": "Use SPF 30+ and reapply",
                        "text": "Reapply every 2 hours; wear a hat and seek shade 11:00-16:00."})
    else:
        actions.append({"icon": "sun", "title": "Use SPF 50+, cover up",
                        "text": "Reapply every 2 hours; avoid direct sun 11:00-16:00."})

    # Hydration
    if hi is not None and hi > 35:
        hyd = "Drink about 250 ml of water every 20-30 minutes outdoors; add electrolytes."
        title = "Hydrate aggressively"
    elif hi is not None and hi > 29:
        hyd, title = "Carry water and sip regularly, even before you feel thirsty.", "Stay hydrated"
    else:
        hyd, title = "Normal water intake is fine.", "Normal hydration"
    if profile_name == "athlete" and hi is not None and hi > 27:
        hyd += " Weigh yourself before/after training to estimate sweat loss."
    actions.append({"icon": "drop", "title": title, "text": hyd})

    # Ventilation / windows
    if aqi is not None and aqi > 100:
        vent = ("Keep windows closed", "Use an air purifier if available; avoid incense and frying smoke indoors.")
    elif aqi is not None and aqi > 50:
        vent = ("Ventilate briefly", "Open windows for short periods, ideally during the best window below.")
    else:
        vent = ("Open windows", "Outdoor air is clean - air out your home.")
    if hum is not None and hum > 70 and not (aqi is not None and aqi > 100):
        vent = (vent[0], vent[1] + " High humidity: run an exhaust fan to prevent damp and mould.")
    actions.append({"icon": "window", "title": vent[0], "text": vent[1]})

    if profile_name == "asthma" and pm25 is not None and pm25 > 12:
        actions.append({"icon": "inhaler", "title": "Carry your reliever inhaler",
                        "text": "PM2.5 above 12 µg/m³ can trigger symptoms in sensitive airways."})

    return {
        "profile": profile_name if profile_name in PROFILES else DEFAULT_PROFILE,
        "profile_label": p["label"],
        "profile_note": p["note"],
        "verdict": verdict,
        "level": level,
        "summary": summary,
        "reasons": unsafe + caution,
        "actions": actions,
    }


# ---------------------------------------------------------------------------
# Best 2-hour window in the next 24 hours
# ---------------------------------------------------------------------------
def best_time_window(hourly: list, now_local: str, window_hours: int = 2,
                     day_start: int = 6, day_end: int = 22):
    """Pick the 2-hour window with the lowest combined AQI + UV + heat index.

    Each factor is scaled to a comparable 0-~1 range:
        AQI/150 + UV/10 + max(0, heat_index - 25)/15
    Only waking hours (06:00-22:00 local) are considered so the answer is
    practical (night-time is often "best" but not useful).
    """
    if not hourly or not now_local:
        return None
    df = pd.DataFrame(hourly)
    if df.empty or "time_local" not in df:
        return None
    df["t"] = pd.to_datetime(df["time_local"], errors="coerce")
    now = pd.to_datetime(now_local[:13] + ":00", errors="coerce")
    if pd.isna(now):
        return None
    df = df[(df["t"] >= now) & (df["t"] < now + pd.Timedelta(hours=24))].copy()
    df = df.dropna(subset=["aqi", "uv", "temperature", "humidity"])
    if len(df) < window_hours:
        return None
    df = df.sort_values("t").reset_index(drop=True)
    df["hi"] = [heat_index_c(t, h) for t, h in zip(df["temperature"], df["humidity"])]
    df["cost"] = df["aqi"] / 150 + df["uv"] / 10 + (df["hi"] - 25).clip(lower=0) / 15

    # cost of a window starting at row i = mean of rows i..i+window-1
    df["win_cost"] = df["cost"].rolling(window_hours).mean().shift(-(window_hours - 1))
    # windows must be consecutive hours and start + end inside waking hours
    df["consecutive"] = (df["t"].shift(-(window_hours - 1)) - df["t"]) == pd.Timedelta(hours=window_hours - 1)
    df["in_day"] = (df["t"].dt.hour >= day_start) & (df["t"].dt.hour + window_hours <= day_end)
    cand = df[df["consecutive"] & df["in_day"] & df["win_cost"].notna()]
    if cand.empty:
        cand = df[df["consecutive"] & df["win_cost"].notna()]
    if cand.empty:
        return None
    i = cand["win_cost"].idxmin()
    win = df.iloc[i:i + window_hours]
    start, end = win["t"].iloc[0], win["t"].iloc[-1] + pd.Timedelta(hours=1)
    same_day = start.date() == now.date()
    return {
        "start": start.strftime("%H:%M"),
        "end": end.strftime("%H:%M"),
        "day": "Today" if same_day else "Tomorrow",
        "start_local": start.strftime("%Y-%m-%dT%H:%M"),
        "avg_aqi": round(float(win["aqi"].mean())),
        "avg_uv": round(float(win["uv"].mean()), 1),
        "avg_heat_index": round(float(win["hi"].mean()), 1),
        "cost": round(float(cand.loc[i, "win_cost"]), 3),
        "hours_considered": int(len(df)),
    }


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
def alerts_for(cur: dict, profile_name: str) -> list:
    p = get_profile(profile_name)
    out = []
    aqi, uv, hi, noise = cur.get("aqi"), cur.get("uv"), cur.get("heat_index"), cur.get("noise")
    if aqi is not None and aqi > p["aqi_alert"]:
        sev = "critical" if aqi > 200 else "warning"
        out.append({"kind": "aqi", "severity": sev, "value": aqi,
                    "title": f"Unhealthy air: AQI {aqi:.0f} (limit {p['aqi_alert']} for {p['label']})",
                    "action": "Wear an N95 outdoors and keep windows closed."})
    if uv is not None and uv >= config.ALERT_UV:
        sev = "critical" if uv >= 11 else "warning"
        out.append({"kind": "uv", "severity": sev, "value": uv,
                    "title": f"Very high UV: index {uv:.0f}",
                    "action": "Avoid sun 11:00-16:00; use SPF 50+ and a hat."})
    if hi is not None and hi > config.ALERT_HEAT_INDEX:
        sev = "critical" if hi > 46 else "warning"
        out.append({"kind": "heat", "severity": sev, "value": hi,
                    "title": f"Dangerous heat: feels like {hi:.0f}°C",
                    "action": "Stay in shade or indoors, drink water every 20 minutes."})
    if noise is not None and noise > config.ALERT_NOISE:
        out.append({"kind": "noise", "severity": "warning", "value": noise,
                    "title": f"Harmful noise: about {noise:.0f} dB",
                    "action": "Move to a quieter place or use ear protection."})
    return out

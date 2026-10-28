"""
Rule-based Environment Analyzer.

1. Converts each raw measurement into a 0-100 sub-score (100 = ideal).
2. Combines the sub-scores with fixed weights into one Environmental
   Health Score (0-100). Missing inputs (e.g. noise not measured) are
   dropped and the remaining weights are renormalised to sum to 1.
3. Assigns colour-coded bands (US EPA AQI, WHO UV, comfort bands).
4. Detects simple patterns (heat stress, stagnant pollution, midday sun,
   harmful noise) and explains them in plain English.
"""
import numpy as np

import config

# ---------------------------------------------------------------------------
# Heat index (feels-like from temperature + humidity), NOAA / NWS method
# ---------------------------------------------------------------------------
def heat_index_c(temp_c, rh):
    """Heat index in deg C using the NWS Rothfusz regression (with the
    standard low-temperature and humidity adjustments)."""
    if temp_c is None or rh is None:
        return temp_c
    t = temp_c * 9 / 5 + 32
    simple = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + rh * 0.094)
    if (simple + t) / 2 < 80:
        hi = simple
    else:
        hi = (-42.379 + 2.04901523 * t + 10.14333127 * rh - 0.22475541 * t * rh
              - 0.00683783 * t * t - 0.05481717 * rh * rh + 0.00122874 * t * t * rh
              + 0.00085282 * t * rh * rh - 0.00000199 * t * t * rh * rh)
        if rh < 13 and 80 <= t <= 112:
            hi -= ((13 - rh) / 4) * np.sqrt((17 - abs(t - 95)) / 17)
        elif rh > 85 and 80 <= t <= 87:
            hi += ((rh - 85) / 10) * ((87 - t) / 5)
    return round((hi - 32) * 5 / 9, 1)


# ---------------------------------------------------------------------------
# Sub-score curves: (x points, score points); np.interp does the rest.
# ---------------------------------------------------------------------------
SUBSCORE_CURVES = {
    "aqi":        ([0, 50, 100, 150, 200, 300, 500], [100, 85, 60, 35, 20, 5, 0]),
    "heat_index": ([-10, 0, 10, 18, 27, 32, 39, 46, 54], [10, 40, 70, 100, 100, 70, 40, 10, 0]),
    "uv":         ([0, 2, 5, 7, 10, 11, 14], [100, 100, 75, 50, 20, 10, 0]),
    "humidity":   ([0, 10, 20, 30, 60, 70, 80, 90, 100], [30, 50, 75, 100, 100, 80, 55, 30, 15]),
    "noise":      ([0, 40, 60, 80, 100, 120], [100, 100, 80, 40, 0, 0]),
}


WEAKEST_LINK_MARGIN = 25
CAP_METRICS = ("aqi", "heat_index", "uv")


def subscore(metric, value):
    if value is None:
        return None
    xs, ys = SUBSCORE_CURVES[metric]
    return float(np.interp(value, xs, ys))


# ---------------------------------------------------------------------------
# Bands
# ---------------------------------------------------------------------------
# Each band: (upper bound inclusive, label, css level, advice)
AQI_BANDS = [
    (50, "Good", "good", "Air quality is satisfactory."),
    (100, "Moderate", "moderate", "Acceptable; unusually sensitive people should limit long exertion."),
    (150, "Unhealthy for Sensitive Groups", "usg", "Sensitive groups should reduce outdoor exertion."),
    (200, "Unhealthy", "unhealthy", "Everyone may begin to feel health effects."),
    (300, "Very Unhealthy", "very-unhealthy", "Health alert: everyone may experience serious effects."),
    (float("inf"), "Hazardous", "hazardous", "Emergency conditions: stay indoors."),
]
UV_BANDS = [
    (2.99, "Low", "good", "No protection needed."),
    (5.99, "Moderate", "moderate", "Seek shade at midday; use SPF 30."),
    (7.99, "High", "usg", "Reduce sun 11:00-16:00; SPF 30+, hat, sunglasses."),
    (10.99, "Very High", "unhealthy", "Avoid midday sun; SPF 50+."),
    (float("inf"), "Extreme", "very-unhealthy", "Stay indoors at midday."),
]
TEMP_BANDS = [
    (9.99, "Cold", "cold", "Wear warm layers."),
    (17.99, "Cool", "cool", "A light jacket helps."),
    (26.99, "Comfortable", "good", "Pleasant conditions."),
    (31.99, "Warm", "moderate", "Stay hydrated."),
    (37.99, "Hot", "usg", "Limit strenuous activity; drink water."),
    (float("inf"), "Very Hot", "unhealthy", "Heat risk: stay cool indoors."),
]
HUMIDITY_BANDS = [
    (29.99, "Dry", "moderate", "Dry air can irritate eyes and throat."),
    (60, "Comfortable", "good", "Ideal humidity range."),
    (70, "Humid", "moderate", "Slightly muggy."),
    (float("inf"), "Very Humid", "usg", "Sticky; sweat evaporates poorly."),
]


def _band(value, bands):
    if value is None:
        return {"label": "No data", "level": "none", "advice": ""}
    for upper, label, level, advice in bands:
        if value <= upper:
            return {"label": label, "level": level, "advice": advice}
    return {"label": "No data", "level": "none", "advice": ""}


def noise_band(value):
    if value is None:
        return {"label": "Not measured yet", "level": "none", "advice": ""}
    for upper, label, level in config.NOISE_BANDS:
        if value < upper:
            advice = {
                "Quiet": "Calm surroundings.",
                "Normal": "Typical conversation level.",
                "Loud": "Long exposure is tiring.",
                "Harmful": "Risk of hearing damage with long exposure.",
            }[label]
            return {"label": label, "level": level, "advice": advice}
    return {"label": "Harmful", "level": "unhealthy", "advice": ""}


def bands(cur: dict) -> dict:
    return {
        "aqi": _band(cur.get("aqi"), AQI_BANDS),
        "uv": _band(cur.get("uv"), UV_BANDS),
        "temperature": _band(cur.get("temperature"), TEMP_BANDS),
        "humidity": _band(cur.get("humidity"), HUMIDITY_BANDS),
        "noise": noise_band(cur.get("noise")),
    }


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------
def score_label(score):
    for lower, label, level in config.SCORE_LABELS:
        if score >= lower:
            return label, level
    return "Hazardous", "hazardous"


def health_score(cur: dict) -> dict:
    """Weighted Environmental Health Score with renormalisation."""
    inputs = {
        "aqi": cur.get("aqi"),
        "heat_index": cur.get("heat_index"),
        "uv": cur.get("uv"),
        "humidity": cur.get("humidity"),
        "noise": cur.get("noise"),
    }
    subs = {k: subscore(k, v) for k, v in inputs.items()}
    used = {k: config.SCORE_WEIGHTS[k] for k, s in subs.items() if s is not None}
    total_w = sum(used.values())
    if total_w == 0:
        return {"score": None, "label": "No data", "level": "none",
                "components": [], "noise_included": False}
    eff = {k: w / total_w for k, w in used.items()}
    weighted = sum(subs[k] * eff[k] for k in eff)
    # Weakest-link cap: a weighted average can hide one dangerous factor
    # (e.g. AQI 300 at night with perfect UV). The score may not exceed the
    # worst hazard sub-score by more than WEAKEST_LINK_MARGIN points.
    # Only the major health hazards (AQI, heat, UV) can cap the score; humidity
    # and the approximate noise reading stay purely weighted.
    hazards = [k for k in CAP_METRICS if k in eff]
    if hazards:
        worst_metric = min(hazards, key=lambda k: subs[k])
        cap = subs[worst_metric] + WEAKEST_LINK_MARGIN
    else:
        worst_metric, cap = None, 100.0
    capped = weighted > cap
    score = int(round(max(0.0, min(100.0, min(weighted, cap)))))
    label, level = score_label(score)
    components = []
    for k in config.SCORE_WEIGHTS:
        components.append({
            "metric": k,
            "value": inputs[k],
            "subscore": None if subs[k] is None else round(subs[k], 1),
            "base_weight": config.SCORE_WEIGHTS[k],
            "effective_weight": round(eff.get(k, 0.0), 3),
            "contribution": None if subs[k] is None else round(subs[k] * eff[k], 1),
        })
    return {"score": score, "label": label, "level": level,
            "weighted_score": round(weighted, 1), "capped": capped,
            "limiting_factor": worst_metric if capped else None,
            "components": components, "noise_included": "noise" in eff}


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------
def detect_patterns(cur: dict) -> list:
    out = []
    t, rh, hi = cur.get("temperature"), cur.get("humidity"), cur.get("heat_index")
    pm25, wind, uv, noise = cur.get("pm25"), cur.get("wind"), cur.get("uv"), cur.get("noise")

    if t is not None and rh is not None and ((t >= 30 and rh >= 60) or (hi is not None and hi >= 32)):
        sev = "high" if (hi or t) >= 40 else "medium"
        out.append({
            "kind": "heat_stress", "severity": sev, "title": "Heat stress",
            "detail": f"{t:.0f}°C with {rh:.0f}% humidity feels like {hi:.0f}°C. "
                      "Humid air slows sweat evaporation, so the body cools less effectively.",
        })
    if pm25 is not None and wind is not None and pm25 > 35.4 and wind < 10:
        out.append({
            "kind": "stagnant_pollution", "severity": "high" if pm25 > 55.4 else "medium",
            "title": "Stagnant pollution",
            "detail": f"PM2.5 is {pm25:.0f} µg/m³ while wind is only {wind:.0f} km/h. "
                      "Calm air is not dispersing pollutants, so levels may stay high.",
        })
    if uv is not None and uv >= 6:
        out.append({
            "kind": "midday_sun", "severity": "high" if uv >= 8 else "medium",
            "title": "Midday sun alert",
            "detail": f"UV index {uv:.0f} can burn unprotected skin in about "
                      f"{'15' if uv >= 8 else '25'} minutes. Peak UV is roughly 11:00-15:00.",
        })
    if noise is not None and noise > 80:
        out.append({
            "kind": "harmful_noise", "severity": "high",
            "title": "Harmful noise",
            "detail": f"About {noise:.0f} dB. Long exposure above 80 dB can damage hearing; "
                      "move away or use ear protection.",
        })
    return out


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def enrich(cur: dict) -> dict:
    """Return a copy of the reading with heat_index filled in."""
    c = dict(cur)
    c["heat_index"] = heat_index_c(c.get("temperature"), c.get("humidity"))
    return c


def analyze(cur: dict) -> dict:
    c = enrich(cur)
    return {
        "reading": c,
        "bands": bands(c),
        "score": health_score(c),
        "patterns": detect_patterns(c),
    }


def methodology() -> dict:
    """Weights and threshold tables, shown in the 'How is this calculated?' modal."""
    def rows(ranges, bands_):
        return [{"range": r, "label": b[1], "level": b[2]} for r, b in zip(ranges, bands_)]
    return {
        "weights": config.SCORE_WEIGHTS,
        "weakest_link_margin": WEAKEST_LINK_MARGIN,
        "labels": [{"min": lo, "label": lab, "level": lev} for lo, lab, lev in config.SCORE_LABELS],
        "curves": {k: {"x": v[0], "score": v[1]} for k, v in SUBSCORE_CURVES.items()},
        "aqi": rows(["0 – 50", "51 – 100", "101 – 150", "151 – 200", "201 – 300", "301+"], AQI_BANDS),
        "uv": rows(["0 – 2", "3 – 5", "6 – 7", "8 – 10", "11+"], UV_BANDS),
        "temperature": rows(["< 10 °C", "10 – 17 °C", "18 – 26 °C", "27 – 31 °C", "32 – 37 °C", "38+ °C"],
                            TEMP_BANDS),
        "humidity": rows(["< 30 %", "30 – 60 %", "61 – 70 %", "> 70 %"], HUMIDITY_BANDS),
        "noise": [{"range": "< 40", "label": "Quiet", "level": "good"},
                  {"range": "40 – 60", "label": "Normal", "level": "moderate"},
                  {"range": "60 – 80", "label": "Loud", "level": "usg"},
                  {"range": "> 80", "label": "Harmful", "level": "unhealthy"}],
    }

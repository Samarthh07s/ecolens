from analysis import recommender
from tests.fixtures import weather_response, air_response
from services.open_meteo import normalise


def cur(**kw):
    base = {"aqi": 40, "pm25": 8, "temperature": 24, "humidity": 50, "uv": 1, "heat_index": 24, "noise": None}
    base.update(kw)
    return base


def test_clean_air_is_safe():
    r = recommender.recommend(cur(), "general")
    assert r["verdict"] == "Safe"
    assert any(a["title"] == "No mask needed" for a in r["actions"])


def test_asthma_is_stricter_than_general():
    c = cur(aqi=120)
    assert recommender.recommend(c, "general")["verdict"] == "Take precautions"
    assert recommender.recommend(c, "asthma")["verdict"] == "Avoid"


def test_general_avoid_above_150():
    r = recommender.recommend(cur(aqi=170), "general")
    assert r["verdict"] == "Avoid"
    assert any("N95" in a["title"] for a in r["actions"])
    assert any("Avoid outdoor exercise" == a["title"] for a in r["actions"])


def test_sunscreen_advice_scales_with_uv():
    titles = lambda uv: [a["title"] for a in recommender.recommend(cur(uv=uv), "general")["actions"]]
    assert "Sunscreen optional" in titles(1)
    assert "Use SPF 30" in titles(4)
    assert "Use SPF 50+, cover up" in titles(9)


def test_unknown_profile_falls_back_to_general():
    assert recommender.recommend(cur(), "hacker'; DROP TABLE")["profile"] == "general"


def test_alert_thresholds_depend_on_profile():
    c = cur(aqi=120)
    assert recommender.alerts_for(c, "general") == []
    kinds = [a["kind"] for a in recommender.alerts_for(c, "children")]
    assert kinds == ["aqi"]


def test_alerts_for_uv_heat_noise():
    kinds = {a["kind"] for a in recommender.alerts_for(cur(uv=8, heat_index=42, noise=85), "general")}
    assert kinds == {"uv", "heat", "noise"}
    assert recommender.alerts_for(cur(uv=7.9, heat_index=40, noise=80), "general") == []


def test_best_window_picks_lowest_cost_daytime_hours():
    data = normalise(weather_response(), air_response())
    best = recommender.best_time_window(data["hourly"], data["current"]["time_local"])
    assert best is not None
    start_h = int(best["start"][:2])
    assert 6 <= start_h <= 20                     # waking hours only
    # end is exactly two hours after start
    assert (int(best["end"][:2]) - start_h) % 24 == 2


def test_best_window_handles_missing_data():
    assert recommender.best_time_window([], "2026-10-24T10:00") is None

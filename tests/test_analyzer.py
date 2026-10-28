import pytest

import config
from analysis import analyzer


def reading(**kw):
    base = {"aqi": 40, "pm25": 8, "pm10": 20, "temperature": 24, "humidity": 50, "uv": 1, "wind": 12}
    base.update(kw)
    return base


def test_heat_index_matches_noaa_reference():
    # NOAA table: 90 F (32.2 C) at 60% RH -> heat index ~100 F (37.8 C)
    assert analyzer.heat_index_c(32.2, 60) == pytest.approx(37.8, abs=0.8)
    # Below ~27 C the heat index is close to air temperature
    assert analyzer.heat_index_c(20, 50) == pytest.approx(20, abs=1.5)


def test_weights_sum_to_one():
    assert sum(config.SCORE_WEIGHTS.values()) == pytest.approx(1.0)


def test_ideal_conditions_score_excellent():
    s = analyzer.analyze(reading())["score"]
    assert s["score"] >= 90
    assert s["label"] == "Excellent"


def test_score_is_bounded_and_monotonic_in_aqi():
    scores = [analyzer.analyze(reading(aqi=a))["score"]["score"] for a in (10, 80, 160, 260, 450)]
    assert all(0 <= s <= 100 for s in scores)
    assert scores == sorted(scores, reverse=True)


def test_noise_excluded_renormalises_weights():
    s = analyzer.analyze(reading(noise=None))["score"]
    assert s["noise_included"] is False
    used = [c["effective_weight"] for c in s["components"] if c["subscore"] is not None]
    assert sum(used) == pytest.approx(1.0, abs=0.01)
    aqi = next(c for c in s["components"] if c["metric"] == "aqi")
    assert aqi["effective_weight"] == pytest.approx(0.40 / 0.95, abs=0.001)


def test_noise_included_when_measured():
    quiet = analyzer.analyze(reading(noise=35))["score"]
    loud = analyzer.analyze(reading(noise=95))["score"]
    assert quiet["noise_included"] and loud["noise_included"]
    assert loud["score"] < quiet["score"]


def test_weakest_link_cap_hides_nothing():
    # Perfect everything except hazardous air: must not look "Good"
    s = analyzer.analyze(reading(aqi=320))["score"]
    assert s["capped"] is True and s["limiting_factor"] == "aqi"
    assert s["label"] in ("Poor", "Hazardous")


def test_noise_never_caps_score():
    s = analyzer.analyze(reading(noise=110))["score"]
    assert s["capped"] is False


@pytest.mark.parametrize("aqi,label", [(30, "Good"), (75, "Moderate"), (120, "Unhealthy for Sensitive Groups"),
                                       (180, "Unhealthy"), (250, "Very Unhealthy"), (400, "Hazardous")])
def test_aqi_bands(aqi, label):
    assert analyzer.analyze(reading(aqi=aqi))["bands"]["aqi"]["label"] == label


@pytest.mark.parametrize("uv,label", [(1, "Low"), (4, "Moderate"), (6.5, "High"), (9, "Very High"), (12, "Extreme")])
def test_uv_bands(uv, label):
    assert analyzer.analyze(reading(uv=uv))["bands"]["uv"]["label"] == label


@pytest.mark.parametrize("db,label", [(None, "Not measured yet"), (30, "Quiet"), (50, "Normal"), (70, "Loud"), (85, "Harmful")])
def test_noise_bands(db, label):
    assert analyzer.noise_band(db)["label"] == label


def test_pattern_heat_stress():
    kinds = {p["kind"] for p in analyzer.analyze(reading(temperature=34, humidity=70))["patterns"]}
    assert "heat_stress" in kinds


def test_pattern_stagnant_pollution():
    kinds = {p["kind"] for p in analyzer.analyze(reading(pm25=60, wind=4, aqi=155))["patterns"]}
    assert "stagnant_pollution" in kinds
    windy = {p["kind"] for p in analyzer.analyze(reading(pm25=60, wind=25, aqi=155))["patterns"]}
    assert "stagnant_pollution" not in windy


def test_pattern_midday_sun_and_noise():
    kinds = {p["kind"] for p in analyzer.analyze(reading(uv=9, noise=88))["patterns"]}
    assert {"midday_sun", "harmful_noise"} <= kinds


def test_no_patterns_in_good_conditions():
    assert analyzer.analyze(reading())["patterns"] == []


def test_methodology_has_all_tables():
    m = analyzer.methodology()
    for k in ("weights", "aqi", "uv", "temperature", "humidity", "noise", "labels"):
        assert m[k]

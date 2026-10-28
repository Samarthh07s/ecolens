"""API tests. requests.get is replaced with a fake, so no internet is used."""
import pytest
import requests

import app as ecolens
import database as db
from tests.fixtures import make_fake_get


@pytest.fixture
def client():
    ecolens.app.config["TESTING"] = True
    return ecolens.app.test_client()


@pytest.fixture
def fake_api(monkeypatch):
    def install(**kw):
        fake = make_fake_get(**kw)
        monkeypatch.setattr(requests, "get", fake)
        return fake
    return install


def test_pages_render(client):
    for path in ("/", "/trends", "/compare", "/settings", "/alerts", "/about"):
        r = client.get(path)
        assert r.status_code == 200
        assert b"EcoLens" in r.data
        assert "Content-Security-Policy" in r.headers


def test_profile_preferences_round_trip(client):
    saved = client.put("/api/profile", json={
        "display_name": "Asha", "health_profile": "asthma", "units": "metric"
    })
    assert saved.status_code == 200
    assert saved.get_json()["display_name"] == "Asha"
    assert saved.get_json()["health_profile"] == "asthma"
    loaded = client.get("/api/profile")
    assert loaded.get_json()["display_name"] == "Asha"


def test_profile_rejects_invalid_values(client):
    response = client.put("/api/profile", json={
        "display_name": "x", "health_profile": "not-a-profile", "units": "kelvin"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["health_profile"] == "general"
    assert data["units"] == "metric"


def test_compare_endpoint_returns_two_payloads(client, fake_api):
    fake_api()
    response = client.get("/api/compare", query_string={
        "lat1": 18.52, "lon1": 73.86, "name1": "Pune",
        "lat2": 19.07, "lon2": 72.88, "name2": "Mumbai",
        "profile": "general",
    })
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["locations"]) == 2
    assert data["locations"][0]["location"]["name"] == "Pune"
    assert data["locations"][1]["location"]["name"] == "Mumbai"


def test_current_default_is_pune(client, fake_api):
    fake = fake_api()
    r = client.get("/api/current")
    assert r.status_code == 200
    d = r.get_json()
    assert d["location"]["name"].startswith("Pune")
    assert d["offline"] is False
    assert 0 <= d["analysis"]["score"]["score"] <= 100
    assert d["recommendations"]["verdict"] in ("Safe", "Take precautions", "Avoid")
    assert d["current"]["noise"] is None
    # timeout and past_days are passed to the API
    assert all(c[2] == 8 for c in fake.calls)
    assert any(c[1].get("past_days") == 2 for c in fake.calls)


def test_current_saves_live_and_past_hourly_history(client, fake_api):
    fake_api()
    client.get("/api/current")
    rows = db.fetch_readings()
    sources = {r["source"] for r in rows}
    assert sources == {"live", "hourly"}
    # no forecast (future) hours are stored
    assert max(r["ts"] for r in rows) <= db.iso(db.utc_now())


def test_input_validation(client, fake_api):
    fake_api()
    assert client.get("/api/current?lat=999&lon=0").status_code == 400
    assert client.get("/api/current?lat=abc&lon=0").status_code == 400
    assert client.get("/api/current?lat=nan&lon=0").status_code == 400
    assert client.get("/api/trends?location=1;DROP TABLE readings").status_code == 400
    assert client.post("/api/noise", json={"db": 500}).status_code == 400


def test_name_is_stored_as_text_not_executed(client, fake_api):
    fake_api()
    evil = "<script>alert(1)</script>'); DROP TABLE readings;--"
    r = client.get("/api/current", query_string={"lat": 18.52, "lon": 73.86, "name": evil})
    assert r.status_code == 200
    assert r.get_json()["location"]["name"] == evil      # returned verbatim as JSON data
    assert len(db.fetch_readings()) > 0                   # table still exists


def test_retries_then_offline_cache(client, fake_api, monkeypatch):
    fake_api()
    assert client.get("/api/current").get_json()["offline"] is False
    down = fake_api(fail=True)
    d = client.get("/api/current").get_json()
    assert d["offline"] is True and d["updated_at"]
    assert len(down.calls) == 3                           # 1 try + 2 retries (cache used after weather fails)


def test_offline_without_cache_is_friendly_503(client, fake_api):
    fake_api(fail=True)
    r = client.get("/api/current?lat=10&lon=10")
    assert r.status_code == 503
    assert "internet" in r.get_json()["error"]


def test_search(client, fake_api):
    fake_api()
    assert client.get("/api/search?q=p").get_json()["results"] == []
    res = client.get("/api/search?q=pune").get_json()["results"]
    assert res[0]["name"] == "Pune, Maharashtra, India"


def test_noise_post_updates_score_and_alerts(client, fake_api):
    fake_api()
    client.get("/api/current")
    r = client.post("/api/noise", json={"lat": 18.5204, "lon": 73.8567, "db": 88, "method": "mic"})
    d = r.get_json()
    assert d["saved"] and d["payload"]["current"]["noise"] == 88
    assert d["payload"]["analysis"]["score"]["noise_included"] is True
    assert any(a["kind"] == "noise" for a in d["payload"]["alerts"])


def test_alerts_dedup_per_hour_and_clear(client, fake_api):
    fake_api(aqi_base=230)                                # always > 150
    first = client.get("/api/current").get_json()["alerts"]
    assert any(a["kind"] == "aqi" and a["is_new"] for a in first)
    second = client.get("/api/current").get_json()["alerts"]
    assert all(not a["is_new"] for a in second)
    stored = client.get("/api/alerts").get_json()["alerts"]
    assert len([a for a in stored if a["kind"] == "aqi"]) == 1
    assert client.delete("/api/alerts").get_json()["cleared"] >= 1
    assert client.get("/api/alerts").get_json()["alerts"] == []


def test_profile_changes_alert_threshold(client, fake_api):
    fake_api(aqi_base=95)                                 # AQI between ~100 and ~125 at most hours
    d_gen = client.get("/api/current?profile=general").get_json()
    d_ast = client.get("/api/current?profile=asthma").get_json()
    aqi = d_gen["current"]["aqi"]
    if 100 < aqi <= 150:
        assert not any(a["kind"] == "aqi" for a in d_gen["alerts"])
        assert any(a["kind"] == "aqi" for a in d_ast["alerts"])


def test_trends_history_and_csv(client, fake_api):
    fake_api()
    client.get("/api/current")
    t = client.get("/api/trends?range=7d").get_json()
    assert t["empty"] is False and t["points"] > 24
    h = client.get("/api/history?range=7d").get_json()
    assert h["locations"][0]["location_key"] == "18.52,73.86"
    csv = client.get("/api/export.csv?range=7d")
    assert csv.mimetype == "text/csv"
    assert csv.data.startswith(b"timestamp_utc,location,lat,lon,source,aqi")


def test_csv_formula_injection_is_neutralised(client, fake_api):
    fake_api()
    client.get("/api/current", query_string={"lat": 18.52, "lon": 73.86, "name": "=HYPERLINK(1)"})
    body = client.get("/api/export.csv?range=7d").data.decode()
    assert "'=HYPERLINK" in body

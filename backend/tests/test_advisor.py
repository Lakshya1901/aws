"""Handler-level tests for GET /risk, POST /recommend, POST /plan, GET /impact (M3).

Market data, weather and routes here are synthetic and TEST ONLY (written to tmp_path). Stored request/response
pairs live in api_fixtures/; regenerate with UPDATE_API_FIXTURES=1 after an intended change and review the diff.
"""
import csv
import json
import os
import pathlib
import sys
import types

import pytest

from backend.adapters import store
from backend.core.netvalue import haversine_km
from backend.handlers import advisor
from backend.tests.fixtures import AS_OF, ORIGIN, glut_day, history, normal_week

FIXTURES = pathlib.Path(__file__).parent / "api_fixtures"
REPO = pathlib.Path(__file__).resolve().parents[2]
TEST_SPEED_KMPH = 40  # TEST ONLY: drive time for the synthetic routes cache, not a sourced value


def stale_week():
    return [r for r in normal_week() if r["market_id"] != "kolar"] + history("kolar", 100, 20, end="2025-04-01")


def price_crash():
    # Kolar-like: arrivals normal (R ~ 1), price down > 25% in 3 days.
    kolar = history("kolar", 100, 20)
    for r in kolar[-3:]:
        r["modal_price_kg"] *= 0.6
    return kolar + history("chintamani", 50, 20) + history("bengaluru", 300, 20) + history("madanapalle", 80, 20)


def ten_loads():
    return (history("kolar", 100, 20, last7_mult=2.5) + history("chintamani", 3, 20)
            + history("bengaluru", 300, 20) + history("madanapalle", 4, 20))


DATASETS = {"normal_week": normal_week, "glut_day": glut_day, "stale_week": stale_week,
            "price_crash": price_crash, "ten_loads": ten_loads}


def synthetic_routes_test_only(origins):
    """TEST ONLY routes cache: haversine x 1.3 and TEST_SPEED_KMPH, for every configured market and outlet."""
    dests = (json.loads((REPO / "config/markets.json").read_text())["markets"]
             + json.loads((REPO / "config/outlets.json").read_text())["outlets"])
    cache = {"_note": "TEST ONLY synthetic routes, not Amazon Location"}
    for lat, lon in origins:
        for d in dests:
            km = haversine_km(lat, lon, d["lat"], d["lon"]) * 1.3
            cache[f"{lat:.3f},{lon:.3f}|{d.get('market_id') or d['outlet_id']}"] = {
                "distance_km": round(km, 2), "drive_hours": round(km / TEST_SPEED_KMPH, 3), "source": "test_only"}
    return cache


def synthetic_weather_test_only(day, temp_c=30.0):
    """TEST ONLY weather snapshot: one point at Kolar with a flat temperature for `day`."""
    return {"_note": "TEST ONLY", "from": day, "to": day, "markets": {"kolar": {
        "lat": 13.1367, "lon": 78.1337, "time": [f"{day}T{h:02d}:00" for h in range(24)],
        "temperature_c": [temp_c] * 24}}}


@pytest.fixture
def api(tmp_path, monkeypatch):
    """Point the advisor at a tmp snapshot; returns setup(dataset) and call(method, path, query, body)."""
    for k in ("PLANS_FILE", "BEDROCK_ENABLED", "CONFIG_DIR"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DATA_SOURCE", "snapshot")
    monkeypatch.setenv("REPLAY_DATE", AS_OF)
    monkeypatch.setenv("PLAN_ID_DETERMINISTIC", "1")
    monkeypatch.setattr(store, "_plans", {})
    routes = tmp_path / "routes.json"
    routes.write_text(json.dumps(synthetic_routes_test_only([(ORIGIN["lat"], ORIGIN["lon"])])))
    monkeypatch.setenv("ROUTES_CACHE", str(routes))

    def setup(dataset):
        snap = tmp_path / dataset
        snap.mkdir(exist_ok=True)
        with open(snap / "test_tomato_synthetic.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, ["date", "market_id", "crop", "arrivals_t", "modal_price_kg"])
            w.writeheader()
            w.writerows(dict(r, crop="tomato") for r in DATASETS[dataset]())
        (snap / "weather_test.json").write_text(json.dumps(synthetic_weather_test_only(AS_OF)))
        monkeypatch.setenv("SNAPSHOT_DIR", str(snap))

    def call(method, path, query=None, body=None):
        event = {"version": "2.0", "rawPath": path, "requestContext": {"http": {"method": method}},
                 "queryStringParameters": query, "body": None if body is None else json.dumps(body)}
        r = advisor.handler(event, None)
        return r["statusCode"], json.loads(r["body"])
    return setup, call


def _recommend_body(**kw):
    return dict({"crop": "tomato", "quantity_kg": 2000, "origin": dict(ORIGIN), "harvest": "today",
                 "language": "en"}, **kw)


def _plan_body():
    qs = [3000, 2500, 2000, 2000, 1500, 1500, 1200, 1000, 800, 500]
    return {"language": "en", "loads": [dict(_recommend_body(quantity_kg=q), load_id=f"L{i}") for i, q in enumerate(qs)]}


CASES = {
    "risk_normal_week": ("normal_week", "GET", "/risk", {"crop": "tomato", "lat": "13.10", "lon": "78.10"}, None),
    "recommend_normal_week": ("normal_week", "POST", "/recommend", None, _recommend_body()),
    "recommend_glut_day": ("glut_day", "POST", "/recommend", None, _recommend_body()),
    "recommend_price_crash_hi": ("price_crash", "POST", "/recommend", None, _recommend_body(language="hi")),
    "recommend_stale": ("stale_week", "POST", "/recommend", None, _recommend_body()),
    "recommend_422_no_markets": ("normal_week", "POST", "/recommend", None,
                                 _recommend_body(origin={"lat": 28.61, "lon": 77.21, "place": "Delhi"})),
    "recommend_422_crop_not_configured": ("normal_week", "POST", "/recommend", None, _recommend_body(crop="onion")),
    "recommend_422_drive_time": ("normal_week", "POST", "/recommend", None,
                                 _recommend_body(origin={"lat": 13.2, "lon": 78.2, "place": "no cached route"})),
    "recommend_422_origin_unknown": ("normal_week", "POST", "/recommend", None,
                                     _recommend_body(origin={"lat": None, "lon": None, "place": "Holur"})),
    "plan_ten_loads": ("ten_loads", "POST", "/plan", None, _plan_body()),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_stored_fixture(api, name):
    setup, call = api
    dataset, method, path, query, body = CASES[name]
    setup(dataset)
    status, resp = call(method, path, query, body)
    f = FIXTURES / f"{name}.json"
    stored = {"dataset": dataset, "request": {"method": method, "path": path, "query": query, "body": body},
              "response": {"status": status, "body": resp}}
    if os.environ.get("UPDATE_API_FIXTURES") == "1":
        f.write_text(json.dumps(stored, indent=1, ensure_ascii=False) + "\n")
    assert json.loads(f.read_text()) == stored


def test_impact_after_plan_matches_plan_total(api):
    setup, call = api
    setup("ten_loads")
    _, p = call("POST", "/plan", body=_plan_body())
    status, imp = call("GET", "/impact", {"plan_id": p["plan_id"]})
    assert status == 200 and imp == dict(p["impact"], plan_id=p["plan_id"])
    assert call("GET", "/impact", {"plan_id": "p_missing"})[0] == 404


def test_impact_sums_recommendations_in_one_plan(api):
    setup, call = api
    setup("glut_day")
    _, a = call("POST", "/recommend", body=_recommend_body())
    _, b = call("POST", "/recommend", body=_recommend_body(quantity_kg=1000, plan_id=a["plan_id"]))
    assert b["plan_id"] == a["plan_id"]
    _, imp = call("GET", "/impact", {"plan_id": a["plan_id"]})
    assert imp["redirected_kg"] == a["impact"]["redirected_kg"] + b["impact"]["redirected_kg"]
    rec = store.get_plan(a["plan_id"])
    assert len(rec["recommendations"]) == 2 and rec["recommendations"][0]["explanation"]["source"] == "template"
    assert "explanation_inputs" in rec["recommendations"][0]


def test_plan_id_deterministic_only_when_asked(api, monkeypatch):
    setup, call = api
    setup("normal_week")
    assert call("POST", "/recommend", body=_recommend_body())[1]["plan_id"] == \
        call("POST", "/recommend", body=_recommend_body())[1]["plan_id"]
    monkeypatch.delenv("PLAN_ID_DETERMINISTIC")
    assert call("POST", "/recommend", body=_recommend_body())[1]["plan_id"] != \
        call("POST", "/recommend", body=_recommend_body())[1]["plan_id"]


def test_plan_logs_overrides(api):
    setup, call = api
    setup("ten_loads")
    body = _plan_body()
    body["loads"][0].update(chosen_outlet_id="kolar", override=True)
    _, p = call("POST", "/plan", body=body)
    rec = store.get_plan(p["plan_id"])
    assert rec["overrides"] == [{"load_id": "L0", "recommended_outlet_id": p["allocations"][0]["outlet"]["outlet_id"],
                                 "chosen_outlet_id": "kolar", "override": True}]


def test_template_cites_arrival_multiple_only_when_ratio_drives_risk(api):
    setup, call = api
    setup("glut_day")
    _, glut = call("POST", "/recommend", body=_recommend_body())
    assert glut["default"]["risk_level"] == "glut" and "x its usual" in glut["explanation"]["text"]
    setup("price_crash")
    _, crash = call("POST", "/recommend", body=_recommend_body())
    d = crash["default"]
    assert d["risk_level"] == "watch" and d["arrival_ratio"] < 1.3
    text = crash["explanation"]["text"]
    assert "x its usual" not in text and f"{d['arrival_ratio']:.1f}" not in text
    assert f"{round(d['price_change_3d'] * 100)}% in 3 days" in text


def test_bedrock_used_when_enabled_else_template(api, monkeypatch):
    setup, call = api
    setup("glut_day")
    stub = types.ModuleType("backend.adapters.bedrock")
    seen = {}

    def explain(facts, language):
        seen["facts"] = facts
        return {"text": "stub", "language": language, "source": "bedrock"}
    stub.explain = explain
    monkeypatch.setitem(sys.modules, "backend.adapters.bedrock", stub)
    assert call("POST", "/recommend", body=_recommend_body())[1]["explanation"]["source"] == "template"
    monkeypatch.setenv("BEDROCK_ENABLED", "1")
    assert call("POST", "/recommend", body=_recommend_body())[1]["explanation"] == \
        {"language": "en", "text": "stub", "source": "bedrock"}
    assert "arrival_ratio" in seen["facts"]["default"]

    def boom(facts, language):
        raise TimeoutError
    stub.explain = boom
    assert call("POST", "/recommend", body=_recommend_body())[1]["explanation"]["source"] == "template"


def test_bad_requests(api):
    setup, call = api
    setup("normal_week")
    assert call("GET", "/risk", {})[0] == 400
    assert call("POST", "/recommend", body=_recommend_body(quantity_kg=-1))[0] == 400
    assert call("POST", "/recommend", body=_recommend_body(language="fr"))[0] == 400
    assert call("POST", "/plan", body={"loads": []})[0] == 400
    assert call("GET", "/nope")[0] == 404


def test_plans_file_persists_between_processes(api, tmp_path, monkeypatch):
    setup, call = api
    setup("normal_week")
    monkeypatch.setenv("PLANS_FILE", str(tmp_path / "plans.json"))
    _, r = call("POST", "/recommend", body=_recommend_body())
    monkeypatch.setattr(store, "_plans", {})
    assert call("GET", "/impact", {"plan_id": r["plan_id"]})[0] == 200


def test_smoke_real_snapshot_replay_day(tmp_path, monkeypatch):
    """Real CEDA snapshot on the replay day with TEST ONLY routes and weather. Structure only, no numbers."""
    snap = tmp_path / "snap"
    snap.mkdir()
    for f in (REPO / "data/snapshot").glob("*.csv"):
        (snap / f.name).symlink_to(f)
    day = json.loads((REPO / "config/model.json").read_text())["replay_date"]
    assert day == "2025-02-07"
    (snap / "weather_test.json").write_text(json.dumps(synthetic_weather_test_only(day)))
    (tmp_path / "routes.json").write_text(json.dumps(synthetic_routes_test_only([(ORIGIN["lat"], ORIGIN["lon"])])))
    for k, v in {"SNAPSHOT_DIR": str(snap), "ROUTES_CACHE": str(tmp_path / "routes.json"),
                 "DATA_SOURCE": "snapshot"}.items():
        monkeypatch.setenv(k, v)
    for k in ("REPLAY_DATE", "PLANS_FILE", "BEDROCK_ENABLED", "CONFIG_DIR"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(store, "_plans", {})

    def call(method, path, query=None, body=None):
        r = advisor.handler({"rawPath": path, "requestContext": {"http": {"method": method}},
                             "queryStringParameters": query, "body": json.dumps(body) if body else None}, None)
        return r["statusCode"], json.loads(r["body"])

    s, risk = call("GET", "/risk", {"crop": "tomato", "lat": "13.10", "lon": "78.10"})
    assert s == 200 and risk["replay_date"] == day and risk["data"]["as_of_date"] == day
    assert {"crop", "mode", "replay_date", "unit_box_kg", "markets"} <= set(risk)
    assert risk["markets"] and {"market_id", "name", "risk_level", "arrival_ratio", "modal_price_rs_per_kg",
                                "price_change_3d", "stale", "distance_km", "distance_approx"} <= set(risk["markets"][0])
    for lang in ("en", "hi", "kn"):
        s, r = call("POST", "/recommend", body=_recommend_body(language=lang))
        assert s == 200 and r["explanation"]["language"] == lang and r["explanation"]["text"]
        assert {"plan_id", "mode", "replay_date", "demo_loads", "data", "top", "default", "alternatives", "impact",
                "advice", "harvest_cost_rs_per_kg", "assumptions_used"} <= set(r)
        assert r["default"]["outlet_id"] == "kolar"
    s, p = call("POST", "/plan", body=_plan_body())
    assert s == 200 and len(p["allocations"]) == 10 and p["markets"]
    assert call("GET", "/impact", {"plan_id": p["plan_id"]})[0] == 200


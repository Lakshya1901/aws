import copy

import pytest

from backend.core.config import CoreError
from backend.core.recommend import glut_radar, plan, recommend
from backend.core.risk import market_risk, projected_ratio
from backend.tests.fixtures import AS_OF, MARKETS, OUTLETS, glut_day, history, load, normal_week


def test_normal_week_one_load_goes_to_nearest_mandi(configs):
    r = recommend(load(), normal_week(), MARKETS, OUTLETS, configs, AS_OF)
    assert r["mode"] == "same_day"
    assert r["data"] == {"as_of_date": AS_OF, "stale": False}
    assert r["default"]["outlet_id"] == "kolar"
    assert r["top"]["outlet_id"] == "kolar"
    assert r["impact"]["redirected_kg"] == 0
    assert r["impact"]["waste_avoided_kg"] == {"low": 0, "mid": 0, "high": 0}
    assert r["advice"] is None
    assert "explanation" not in r


def test_glut_day_2000kg_goes_to_alternative(configs):
    r = recommend(load(2000), glut_day(), MARKETS, OUTLETS, configs, AS_OF)
    assert r["default"]["outlet_id"] == "kolar" and r["default"]["risk_level"] == "glut"
    assert r["top"]["outlet_id"] != "kolar" and r["top"]["type"] == "mandi"
    w = r["impact"]["waste_avoided_kg"]
    assert 0 < w["mid"] < 2000
    assert w["low"] <= w["mid"] <= w["high"]
    assert r["impact"]["redirected_kg"] == 2000
    assert r["impact"]["extra_km"] > 0
    assert r["impact"]["diesel_l"] == pytest.approx(r["impact"]["extra_km"] * 0.14, rel=1e-3)
    assert r["impact"]["co2_kg"] == pytest.approx(r["impact"]["diesel_l"] * 2.68, rel=1e-3)
    assert r["impact"]["water_l"] == pytest.approx(w["mid"] * 184, rel=1e-3)
    assert "dump_share_table" in r["assumptions_used"]
    ranked = [o["net_rs_per_kg"]["mid"] for o in r["alternatives"] if o["type"] == "mandi"]
    assert ranked == sorted(ranked, reverse=True)


def test_waste_avoided_and_redirected_are_separate_keys(configs):
    r = recommend(load(2000), glut_day(), MARKETS, OUTLETS, configs, AS_OF)
    assert "waste_avoided_kg" in r["impact"] and "redirected_kg" in r["impact"]
    assert isinstance(r["impact"]["waste_avoided_kg"], dict)
    assert r["impact"]["redirected_kg"] != r["impact"]["waste_avoided_kg"]["mid"]
    p = plan([load(2000), load(1000)], glut_day(), MARKETS, OUTLETS, configs, AS_OF)
    assert "waste_avoided_kg" in p["impact"] and "redirected_kg" in p["impact"]


def _never_pushed_into_glut(p, rows, configs):
    for market_id, kg in p["dA_kg"]["tomato"].items():
        risk = market_risk([r for r in rows if r["market_id"] == market_id], AS_OF,
                           configs["model"], configs["assumptions"])
        before = risk["risk_level"]
        after = projected_ratio(risk, kg / 1000)
        assert before == "glut" or after < configs["model"]["risk"]["glut_ratio"], market_id


def test_glut_day_ten_loads_split_and_never_push_into_glut(configs):
    rows = (history("kolar", 100, 20, last7_mult=2.5) + history("chintamani", 3, 20)
            + history("bengaluru", 300, 20) + history("madanapalle", 4, 20))
    loads = [load(q, load_id=f"L{i}") for i, q in enumerate([3000, 2500, 2000, 2000, 1500, 1500, 1200, 1000, 800, 500])]
    p = plan(loads, rows, MARKETS, OUTLETS, configs, AS_OF)
    tops = {a["top"]["outlet_id"] for a in p["allocations"]}
    assert len(tops) >= 2
    assert "kolar" not in tops
    assert [a["load_id"] for a in p["allocations"]] == [f"L{i}" for i in range(10)]
    assert sum(p["dA_kg"]["tomato"].values()) == sum(l["quantity_kg"] for l in loads)
    _never_pushed_into_glut(p, rows, configs)
    assert p["impact"]["redirected_kg"] == sum(l["quantity_kg"] for l in loads)


def test_small_market_becomes_overloaded(configs):
    # Small market pays far more and its price barely reacts, so only the glut rule stops herding there.
    rows = (history("kolar", 100, 20) + history("chintamani", 3, 40, b=-0.1, noise=0.0)
            + history("bengaluru", 300, 20) + history("madanapalle", 80, 20))
    loads = [load(3000, load_id=f"L{i}") for i in range(10)]
    p = plan(loads, rows, MARKETS, OUTLETS, configs, AS_OF)
    to_small = [a for a in p["allocations"] if a["top"]["outlet_id"] == "chintamani"]
    assert 0 < len(to_small) < 10
    _never_pushed_into_glut(p, rows, configs)
    others = [a for a in p["allocations"] if a["top"]["outlet_id"] != "chintamani"]
    # Loads moved off chintamani while it still had a positive net: the glut rule did it.
    assert any(o["outlet_id"] == "chintamani" and o["projected_risk_level"] == "glut"
               for a in others for o in a["alternatives"])


def test_all_fresh_negative_goes_to_processor_then_food_bank(configs):
    # Prices below the freight cost to even the nearest mandi.
    rows = (history("kolar", 100, 0.05) + history("chintamani", 50, 0.05) + history("bengaluru", 300, 0.05)
            + history("madanapalle", 80, 0.05))
    r = recommend(load(), rows, MARKETS, OUTLETS, configs, AS_OF)
    assert r["top"]["type"] == "processor"
    assert r["top"]["net_rs_per_kg"] is None and r["top"]["net_note"] == "not yet estimated"
    r2 = recommend(load(), rows, MARKETS, [o for o in OUTLETS if o["type"] != "processor"], configs, AS_OF)
    assert r2["top"]["type"] == "food_bank"
    assert r2["top"]["net_rs_per_kg"]["mid"] <= 0  # P_hat 0 minus freight
    assert r2["impact"]["redirected_kg"] == 2000
    assert r2["advice"]["code"] == "harvest_to_order"


def test_storable_crop_holds_when_no_fresh_market_pays(configs):
    c = copy.deepcopy(configs)
    c["crops"]["tomato"]["storable"] = True
    # Prices below the freight cost to even the nearest mandi.
    rows = (history("kolar", 100, 0.05) + history("chintamani", 50, 0.05) + history("bengaluru", 300, 0.05)
            + history("madanapalle", 80, 0.05))
    r = recommend(load(), rows, MARKETS, OUTLETS, c, AS_OF)
    assert r["top"]["type"] == "hold"
    assert r["advice"]["code"] == "delay_harvest"
    assert r["impact"]["waste_avoided_kg"] is None and r["impact"]["water_l"] is None  # not yet estimated, never 0


def test_harvest_cost_above_best_net_gives_advice(configs):
    rows = (history("kolar", 100, 4) + history("chintamani", 50, 4) + history("bengaluru", 300, 4)
            + history("madanapalle", 80, 4))
    r = recommend(load(), rows, MARKETS, OUTLETS, configs, AS_OF)
    assert r["top"]["type"] == "mandi"
    assert 0 < r["top"]["net_rs_per_kg"]["mid"] < 4.7
    assert r["advice"] == {"code": "harvest_to_order", "best_net_rs_per_kg": r["top"]["net_rs_per_kg"]["mid"],
                           "harvest_cost_rs_per_kg": 4.7}
    harvested = recommend(load(harvest="harvested"), rows, MARKETS, OUTLETS, configs, AS_OF)
    assert harvested["advice"] is None


def test_stale_data_sets_flag_and_widens_ranges(configs):
    fresh = recommend(load(), normal_week(), MARKETS, OUTLETS, configs, AS_OF)
    stale_rows = [r for r in normal_week() if r["market_id"] != "kolar"] + history("kolar", 100, 20, end="2025-04-01")
    stale = recommend(load(), stale_rows, MARKETS, OUTLETS, configs, AS_OF)
    assert stale["data"]["stale"] is True
    k_fresh, k_stale = fresh["default"]["price_rs_per_kg"], stale["default"]["price_rs_per_kg"]
    assert stale["default"]["stale"] is True
    from math import log
    w_fresh = log(k_fresh["high"] / k_fresh["mid"])
    w_stale = log(k_stale["high"] / k_stale["mid"])
    assert w_stale > w_fresh
    assert "stale_range_multiplier" in stale["assumptions_used"]


def test_interstate_outlet_uses_destination_state_fees(configs):
    r = recommend(load(), normal_week(), MARKETS, OUTLETS, configs, AS_OF)
    opts = {o["outlet_id"]: o for o in [r["top"], r["default"]] + r["alternatives"]}
    mad, kol = opts["madanapalle"], opts["kolar"]
    assert (mad["state"], mad["fee_pct"], mad["commission_pct"], mad["handling_pct"]) == ("AP", 0.01, 0.04, 0.01)
    assert (kol["state"], kol["fee_pct"], kol["commission_pct"], kol["handling_pct"]) == ("KA", 0.0, 0.05, 0.01)
    p, s = mad["price_rs_per_kg"]["mid"], mad["spoilage_share"]
    expected = p * (1 - s) - mad["freight_rs_per_kg"] - p * (0.01 + 0.04 + 0.01)
    assert mad["net_rs_per_kg"]["mid"] == pytest.approx(expected, abs=1e-3)


def test_routed_distance_used_else_haversine_flagged_approx(configs):
    r = recommend(load(), normal_week(), MARKETS, OUTLETS, configs, AS_OF)
    assert r["top"]["distance_approx"] is True
    routes = {"kolar": {"distance_km": 9.0, "drive_hours": 0.4}}
    r2 = recommend(load(routes=routes), normal_week(), MARKETS, OUTLETS, configs, AS_OF)
    assert r2["top"]["distance_km"] == 9.0 and r2["top"]["drive_hours"] == 0.4
    assert r2["top"]["distance_approx"] is False


def test_no_reporting_markets_in_radius(configs):
    far = load(origin={"lat": 28.61, "lon": 77.21, "place": "Delhi"})
    with pytest.raises(CoreError) as e:
        recommend(far, normal_week(), MARKETS, OUTLETS, configs, AS_OF)
    assert e.value.code == "no_markets_in_radius"


def test_glut_radar(configs):
    out = glut_radar("tomato", glut_day(), MARKETS, configs, AS_OF)
    levels = {m["market_id"]: m["risk_level"] for m in out["markets"]}
    assert levels["kolar"] == "glut" and levels["bengaluru"] == "safe"
    assert out["mode"] == "same_day"


def test_price_crash_without_arrival_spike_prefers_higher_priced_alternative(configs):
    # Real 2025 Kolar pattern: R stays near 1 while the 3-day price change crashes.
    kolar = history("kolar", 100, 20)
    for r in kolar[-3:]:
        r["modal_price_kg"] *= 0.6
    rows = kolar + history("chintamani", 50, 20) + history("bengaluru", 300, 20) + history("madanapalle", 80, 20)
    r = recommend(load(), rows, MARKETS, OUTLETS, configs, AS_OF)
    d = r["default"]
    assert d["outlet_id"] == "kolar" and d["arrival_ratio"] < 1.3 and d["price_change_3d"] < -0.25
    assert d["risk_level"] == "watch"
    assert r["top"]["outlet_id"] != "kolar"
    assert r["top"]["net_rs_per_kg"]["mid"] > d["net_rs_per_kg"]["mid"]
    assert r["impact"]["redirected_kg"] == 2000


def _kolar_crash(kolar_price):
    # Kolar-like crash: arrivals normal (R ~ 1), 3-day price change below -25%.
    kolar = history("kolar", 100, kolar_price)
    for r in kolar[-3:]:
        r["modal_price_kg"] *= 0.6
    return kolar + history("chintamani", 50, 20) + history("bengaluru", 300, 20) + history("madanapalle", 80, 20)


def test_price_below_cost_dump_counts_waste_avoided_when_arrivals_normal(configs):
    r = recommend(load(), _kolar_crash(7), MARKETS, OUTLETS, configs, AS_OF)
    d, t, q = r["default"], r["top"], 2000
    assert d["outlet_id"] == "kolar" and d["arrival_ratio"] < 1.3 and d["risk_level"] == "watch"
    assert d["net_rs_per_kg"]["mid"] < 4.7 and t["outlet_id"] != "kolar"
    w = r["impact"]["waste_avoided_kg"]
    assert 0 < w["mid"] < q and w["low"] <= w["mid"] <= w["high"]
    # u_default = max(u(R)=0, 0.40) mid; advised side keeps u(R) of its band (0 here).
    expected_mid = q * (min(1, d["spoilage_range"]["mid"] + 0.40) - t["spoilage_range"]["mid"])
    assert w["mid"] == pytest.approx(expected_mid, abs=0.5)  # inputs rounded to 4 dp
    assert "below_cost_dump_share" in r["assumptions_used"]


def test_default_net_at_or_above_cost_keeps_u_of_r(configs):
    r = recommend(load(), _kolar_crash(20), MARKETS, OUTLETS, configs, AS_OF)
    d, t = r["default"], r["top"]
    assert d["net_rs_per_kg"]["mid"] >= 4.7 and t["outlet_id"] != "kolar"
    expected_mid = 2000 * (d["spoilage_range"]["mid"] - t["spoilage_range"]["mid"])  # u(R) = 0 on both sides
    assert r["impact"]["waste_avoided_kg"]["mid"] == pytest.approx(expected_mid, abs=0.5)  # inputs rounded to 4 dp
    assert "below_cost_dump_share" not in r["assumptions_used"]

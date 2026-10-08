from math import log

import pytest

from backend.core.netvalue import net_value
from backend.core.pricing import fit_elasticity, price_change_sd, price_on_arrival
from backend.core.risk import market_risk, projected_ratio, risk_level
from backend.core.spoilage import spoilage_share
from backend.tests.fixtures import AS_OF, history


def test_risk_levels_follow_section_9_table(configs):
    t = configs["model"]["risk"]
    assert risk_level(1.0, 0.0, t) == "safe"
    assert risk_level(1.3, 0.0, t) == "watch"
    assert risk_level(1.0, -0.2, t) == "watch"
    assert risk_level(2.0, 0.0, t) == "glut"
    assert risk_level(1.6, -0.3, t) == "glut"
    assert risk_level(1.4, -0.3, t) == "watch"
    assert risk_level(None, -0.3, t) is None


def test_ratio_normal_and_glut(configs):
    normal = market_risk(history("kolar", 100, 20), AS_OF, configs["model"], configs["assumptions"])
    glut = market_risk(history("kolar", 100, 20, last7_mult=2.5), AS_OF, configs["model"], configs["assumptions"])
    assert normal["data_complete"] and normal["risk_level"] == "safe"
    assert 0.8 < normal["arrival_ratio"] < 1.25
    assert glut["risk_level"] == "glut" and glut["arrival_ratio"] > 2.0
    assert glut["price_change_3d"] is not None and not glut["stale"]


def test_missing_days_stay_missing_and_lt5_of_7_is_incomplete(configs):
    skip = ("2025-04-01", "2025-04-02", "2025-04-03")
    rows = history("kolar", 100, 20, skip=skip)
    r = market_risk(rows, AS_OF, configs["model"], configs["assumptions"])
    assert r["days_of_last_7"] == 4
    assert r["data_complete"] is False and r["arrival_ratio"] is None and r["risk_level"] is None
    present = [x["arrivals_t"] for x in rows if "2025-03-29" <= x["date"] <= AS_OF]
    assert len(present) == 4
    assert r["a7_t"] == pytest.approx(sum(present) / 4)  # mean of present days, not /7 with zeros


def test_stale_flag_when_latest_older_than_2_days(configs):
    rows = history("kolar", 100, 20, end="2025-04-01")
    r = market_risk(rows, AS_OF, configs["model"], configs["assumptions"])
    assert r["stale"] is True and r["latest_date"] == "2025-04-01"
    r2 = market_risk(history("kolar", 100, 20, end="2025-04-02"), AS_OF, configs["model"], configs["assumptions"])
    assert r2["stale"] is False


def test_no_lookahead_after_as_of(configs):
    rows = history("kolar", 100, 20, end="2025-04-10")
    r = market_risk(rows, AS_OF, configs["model"], configs["assumptions"])
    assert r["latest_date"] == AS_OF


def test_projected_ratio_adds_tonnes_to_today(configs):
    r = market_risk(history("kolar", 100, 20), AS_OF, configs["model"], configs["assumptions"])
    assert projected_ratio(r, 0) == pytest.approx(r["arrival_ratio"])
    assert projected_ratio(r, 70) == pytest.approx((r["a7_sum_t"] + 70) / 7 / r["baseline_t"])


def test_elasticity_fit_clip_and_fallback(configs):
    m = configs["model"]
    fit = fit_elasticity(history("kolar", 100, 20, b=-0.5), AS_OF, m)
    assert fit["b_source"] == "fit" and fit["b"] == pytest.approx(-0.5, abs=0.05) and fit["resid_sd"] > 0
    steep = fit_elasticity(history("kolar", 100, 20, b=-3.0), AS_OF, m)
    assert steep["b"] == -1.5 and steep["b_source"] == "clipped"
    flat = fit_elasticity(history("kolar", 100, 20, b=0.0, noise=0.1), AS_OF, m)
    assert flat["b"] == -0.5 and flat["b_source"] == "fallback" and flat["r2"] < 0.2


def test_price_on_arrival_falls_with_added_load_and_range_is_one_sd():
    p = price_on_arrival(20, 10, 0, -0.5, 0.1)
    assert p["mid"] == 20
    p2 = price_on_arrival(20, 10, 10, -0.5, 0.1)
    assert p2["mid"] == pytest.approx(20 * 2 ** -0.5)
    assert log(p2["high"] / p2["mid"]) == pytest.approx(0.1)
    assert log(p2["mid"] / p2["low"]) == pytest.approx(0.1)
    wide = price_on_arrival(20, 10, 10, -0.5, 0.1, 1.5)
    assert log(wide["high"] / wide["mid"]) == pytest.approx(0.15)


def test_price_range_sd_is_day_to_day_change_and_skips_gaps():
    rows = [{"date": d, "modal_price_kg": p} for d, p in
            [("2025-04-01", 10), ("2025-04-02", 20), ("2025-04-03", 10), ("2025-04-04", 20), ("2025-04-20", 1)]]
    # changes ln2, -ln2, ln2 (the 16-day gap to 04-20 is skipped): mean ln2/3, sample sd = 2ln2/sqrt(3)
    assert price_change_sd(rows, "2025-04-30", 3) == pytest.approx(2 * log(2) / 3 ** 0.5)
    assert price_change_sd(rows[:3], "2025-04-30", 3) is None
    assert price_change_sd(rows, "2025-04-02", 3) is None


def test_spoilage_increases_with_temperature_and_time(configs):
    tomato = configs["crops"]["tomato"]
    assert spoilage_share(14, 25, tomato)["mid"] == pytest.approx(0.0329, abs=1e-3)  # alpha calibration, ~3.25%
    assert spoilage_share(14, 35, tomato)["mid"] > spoilage_share(14, 25, tomato)["mid"]
    assert spoilage_share(24, 25, tomato)["mid"] > spoilage_share(14, 25, tomato)["mid"]
    s = spoilage_share(14, 25, tomato)
    assert s["low"] < s["mid"] < s["high"]
    assert spoilage_share(10000, 40, tomato)["mid"] == 1.0


def test_transport_cost_scales_with_distance():
    price = {"low": 20, "mid": 20, "high": 20}
    spoil = {"low": 0, "mid": 0, "high": 0}
    n0 = net_value(price, spoil, 0, 11, 0)["mid"]
    n100 = net_value(price, spoil, 100, 11, 0)["mid"]
    n200 = net_value(price, spoil, 200, 11, 0)["mid"]
    assert n0 - n100 == pytest.approx(1.1)
    assert n0 - n200 == pytest.approx(2 * (n0 - n100))


def test_net_value_formula():
    n = net_value({"low": 18, "mid": 20, "high": 22}, {"low": 0.02, "mid": 0.03, "high": 0.05}, 50, 11, 0.06)
    assert n["mid"] == pytest.approx(20 * 0.97 - 0.55 - 20 * 0.06)
    assert n["low"] == pytest.approx(18 * 0.95 - 0.55 - 18 * 0.06)
    assert n["high"] == pytest.approx(22 * 0.98 - 0.55 - 22 * 0.06)

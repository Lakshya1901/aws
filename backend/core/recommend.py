"""Top-level engine entry points shaped like the /risk, /recommend and /plan responses (CLAUDE.md Section 13).

The API layer adds plan_id and explanation, and maps CoreError codes to 422.
"""
from .allocate import allocate, rescue_load
from .config import assumption_entry, crop_mode, get_crop, radar_crop
from .impact import below_cost, total_impact
from .pricing import fit_elasticity
from .risk import market_risk, to_date


def market_context(crop_id, market_days, markets, configs, as_of_date):
    """Reporting markets for a crop: [{"market", "risk", "fit"}].

    A market is used only if it has coordinates (not low confidence), a latest price and arrivals,
    and at least 3 price/arrival days to fit elasticity. Rows with a "crop" key are filtered by it.
    """
    rows_by_market = {}
    for r in market_days:
        if r.get("crop", crop_id) == crop_id:
            rows_by_market.setdefault(r["market_id"], []).append(r)
    ctx = []
    for m in markets:
        rows = rows_by_market.get(m["market_id"])
        if not rows or m.get("lat") is None or m.get("coord_confidence") == "low":
            continue
        risk = market_risk(rows, as_of_date, configs["model"], configs["assumptions"])
        if risk is None or risk["price_kg"] is None or not risk["arrivals_t"]:
            continue
        fit = fit_elasticity(rows, as_of_date, configs["model"])
        if fit["resid_sd"] is None:
            continue
        ctx.append({"market": m, "risk": risk, "fit": fit})
    return ctx


def glut_radar(crop_id, market_days, markets, configs, as_of_date, ctx=None):
    """/risk payload: {"mode", "data", "markets": [risk dict + name, state, lat, lon, elasticity_b]}.

    ctx: precomputed market_context for the crop (MarketRisk, D24); else computed from market_days.
    """
    radar_crop(configs, crop_id)
    if ctx is None:
        ctx = market_context(crop_id, market_days, markets, configs, as_of_date)
    rows = [dict(c["risk"], name=c["market"].get("name"), state=c["market"]["state"],
                 lat=c["market"]["lat"], lon=c["market"]["lon"], elasticity_b=c["fit"]["b"]) for c in ctx]
    return {"mode": crop_mode(configs["model"], crop_id),
            "data": {"as_of_date": to_date(as_of_date).isoformat(), "stale": any(r["stale"] for r in rows)},
            "markets": _round(rows)}


def _assumptions_used(results, crops, configs):
    a = configs["assumptions"]
    keys = {"max_radius_km"}
    for r in results:
        for o in (r["top"], r["default"]):
            if o.get("distance_km") is None:
                continue
            keys.add("freight_rs_per_tonne_km")
            if o["distance_approx"]:
                keys.add("road_factor")
            if o["type"] == "mandi":
                keys.update(k for k in ("fee_pct", "commission_pct", "handling_pct", "t_wait_h")
                            if assumption_entry(a, k, o["state"])["status"] != "sourced")
            if o.get("stale"):
                keys.add("stale_range_multiplier")
        i = r["impact"]
        if i["waste_avoided_kg"] is not None and i["redirected_kg"]:
            keys.add("dump_share_table")
            if any(o.get("price_only") for o in (r["top"], r["default"])):
                keys.add("price_only_ratio")
            if below_cost(r["default"], crops[r["crop"]].get("harvest_cost_rs_per_kg")):
                keys.add("below_cost_dump_share")
        if i["diesel_l"] is not None:
            keys.update(("diesel_l_per_km", "co2_kg_per_l_diesel"))
    used = {k for k in keys if a[k]["status"] != "sourced"}
    for c in {r["crop"] for r in results}:
        used.update(f"{c}.{f}" for f, s in crops[c].get("status", {}).items() if s != "sourced")
    return sorted(used)


def _stale(result):
    """Prices out of date at the recommended or the nearest market (the two the card compares); alternatives
    further down carry their own stale flag."""
    return any(o.get("stale") for o in (result["top"], result["default"]))


def _prices_date(results):
    """Oldest latest-report date among the recommended and nearest mandis, or None (shown as "Prices from")."""
    dates = [o["latest_date"] for r in results for o in (r["top"], r["default"]) if o.get("latest_date")]
    return min(dates) if dates else None


def plan(loads, market_days, markets, outlets, configs, as_of_date, ctx=None):
    """/plan: allocate all loads together (largest first). See README.md for shapes.

    ctx: {crop_id: precomputed market_context} (MarketRisk, D24); else computed from market_days.
    """
    crop_ids = sorted({l["crop"] for l in loads})
    crops = {c: get_crop(configs, c) for c in crop_ids}
    if ctx is None:
        ctx = {c: market_context(c, market_days, markets, configs, as_of_date) for c in crop_ids}
    results, added = allocate(loads, crops, ctx, outlets, configs)
    return _round({
        "mode": {c: crop_mode(configs["model"], c) for c in crop_ids},
        "data": {"as_of_date": to_date(as_of_date).isoformat(), "stale": any(_stale(r) for r in results),
                 "prices_date": _prices_date(results)},
        "allocations": results,
        "dA_kg": added,
        "impact": total_impact([r["impact"] for r in results]),
        "assumptions_used": _assumptions_used(results, crops, configs),
    })


def recommend(load, market_days, markets, outlets, configs, as_of_date, ctx=None):
    """/recommend for one load (without plan_id and explanation)."""
    p = plan([load], market_days, markets, outlets, configs, as_of_date, ctx)
    r = p["allocations"][0]
    return {"mode": p["mode"][load["crop"]], "data": p["data"], "crop": r["crop"], "quantity_kg": r["quantity_kg"],
            "top": r["top"], "default": r["default"], "alternatives": r["alternatives"],
            "impact": r["impact"], "advice": r["advice"], "assumptions_used": p["assumptions_used"]}


def rescue(load, outlets, configs, as_of_date, ctx=None):
    """/recommend with source mandi_unsold (Step 5b), without plan_id and explanation. ctx: the crop's
    market_context (mandis where the edible part could still sell, D36)."""
    crop = get_crop(configs, load["crop"])
    r = rescue_load(dict(load, as_of_date=to_date(as_of_date).isoformat()), crop, outlets, configs, ctx)
    a = configs["assumptions"]
    keys = {"rescue_radius_km"}
    for o in (r["top"], r["recover"]):
        if o is not None:
            keys.add("freight_rs_per_tonne_km")
            if o["distance_approx"]:
                keys.add("road_factor")
    if r["impact"]["biogas_kg"]:
        keys.add("biogas_yield")
    used = {k for k in keys if a[k]["status"] != "sourced"}
    if r["split"]["source"] == "estimate":
        used.update(f"{crop['crop_id']}.{f}" for f in ("sl_ref_hours", "q10", "alpha")
                    if crop.get("status", {}).get(f, "sourced") != "sourced")
    return _round(dict(r, source="mandi_unsold", data={"as_of_date": to_date(as_of_date).isoformat(), "stale": False},
                       assumptions_used=sorted(used)))


def _round(x, nd=4):
    if isinstance(x, float):
        return round(x, nd)
    if isinstance(x, dict):
        return {k: _round(v, nd) for k, v in x.items()}
    if isinstance(x, list):
        return [_round(v, nd) for v in x]
    return x

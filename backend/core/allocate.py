"""Step 5: greedy allocation across outlets, anti-herding (CLAUDE.md Section 9)."""
from .config import CoreError, assumption
from .risk import to_date
from .impact import EDIBLE_TYPES, RECOVER_TYPES, impact, rescue_impact
from .netvalue import fresh_option, haversine_km, second_life_option
from .spoilage import spoilage_share

SECOND_LIFE_ORDER = EDIBLE_TYPES + RECOVER_TYPES


def _nearest(origin, items, radius_km, limit=None):
    """Items with lat/lon within radius_km straight-line of origin, nearest first, at most limit."""
    scored = sorted(((haversine_km(origin["lat"], origin["lon"], it["lat"], it["lon"]), i, it)
                     for i, it in enumerate(items)), key=lambda t: (t[0], t[1]))
    within = [it for d, _, it in scored if d <= radius_km]
    return within[:limit] if limit else within


def allocate_load(load, crop, market_ctx, outlets, added_kg, configs):
    """Recommend one load given dA so far (added_kg: {market_id: kg}, updated in place).

    market_ctx: [{"market", "risk", "fit"}] for reporting markets of this crop.
    """
    a = configs["assumptions"]
    radius = assumption(a, "max_radius_km")
    near = _nearest(load["origin"], [dict(m["market"], _ctx=m) for m in market_ctx], radius,
                    configs["model"]["nearest_markets"])
    if not near:
        raise CoreError("no_markets_in_radius", "No reporting markets near you for this crop")
    q = load["quantity_kg"]
    # D25: a price older than max_data_age_days says nothing about today's market; list it, never choose it.
    max_age = assumption(a, "max_data_age_days")
    too_old = {m["market_id"] for m in near
               if (to_date(m["_ctx"]["risk"]["as_of_date"]) - to_date(m["_ctx"]["risk"]["latest_date"])).days > max_age}
    fresh = [fresh_option(load, m["_ctx"], added_kg.get(m["market_id"], 0), crop, configs) for m in near]
    fresh.sort(key=lambda o: -o["net_rs_per_kg"]["mid"])
    default = min(fresh, key=lambda o: o["distance_km"])
    # D17: only markets whose projected R is known can be checked for glut, so only they can be chosen.
    paying = [o for o in fresh if o["net_rs_per_kg"]["mid"] > 0 and o["projected_risk_level"] is not None
              and o["outlet_id"] not in too_old]
    # Best paying market whose projected R stays out of glut; if every paying market would be in glut, the best one.
    top = next((o for o in paying if o["projected_risk_level"] != "glut"), paying[0] if paying else None)

    eligible = [o for o in outlets if crop["crop_id"] in o.get("crops", []) and o["type"] in crop["second_life"]]
    second = [second_life_option(load, o, crop, configs) for o in _nearest(load["origin"], eligible, radius)]
    second.sort(key=lambda o: SECOND_LIFE_ORDER.index(o["type"]))  # stable: nearest first within a type

    if top is not None:
        added_kg[top["outlet_id"]] = added_kg.get(top["outlet_id"], 0) + q
    elif crop["storable"]:
        top = {"outlet_id": None, "type": "hold", "net_rs_per_kg": None, "net_note": "not yet estimated"}
    elif second:
        top = second[0]
    else:
        top = {"outlet_id": None, "type": "compost", "net_rs_per_kg": None,
               "net_note": "not yet estimated", "note": "No seeded second-life outlet in radius"}

    best_net = fresh[0]["net_rs_per_kg"]["mid"]
    advice = None
    cost = crop.get("harvest_cost_rs_per_kg")  # optional (D33): without it there is no harvest advice
    if load.get("harvest") != "harvested" and cost is not None and best_net < cost:
        advice = {"code": "delay_harvest" if crop["storable"] else "harvest_to_order",
                  "best_net_rs_per_kg": best_net, "harvest_cost_rs_per_kg": crop["harvest_cost_rs_per_kg"]}
    return {
        "load_id": load.get("load_id"), "crop": crop["crop_id"], "quantity_kg": q,
        "top": top, "default": default,
        "alternatives": [o for o in fresh + second if o is not top],
        "impact": impact(q, default, top, crop, a),
        "advice": advice,
    }


def rescue_load(load, crop, outlets, configs):
    """Step 5b: unsold stock at a city mandi. Edible part -> processor, then food bank; spoiled part (and the edible
    part when no processor or food bank is in radius) -> feed, then biogas, then compost. Fresh mandis are not ranked.

    load["split"] = {"edible_kg", "spoiled_kg"} from the trader, or None: the engine proposes the spoiled share
    s = min(1, alpha * hours_since_harvest / SL(T)) (Step 3, mid), which needs load["temp_c"].
    """
    q = load["quantity_kg"]
    if load.get("split") is not None:
        split = dict(load["split"], source="trader")
    elif load.get("temp_c") is None:
        raise CoreError("split_required", "No weather data here to estimate spoilage; enter edible and spoiled kg")
    else:
        s = spoilage_share(load["hours_since_harvest"], load["temp_c"], crop)["mid"]
        split = {"edible_kg": q * (1 - s), "spoiled_kg": q * s, "source": "estimate"}
    eligible = [o for o in outlets if crop["crop_id"] in o.get("crops", []) and o["type"] in crop["second_life"]]
    near = _nearest(load["origin"], eligible, assumption(configs["assumptions"], "rescue_radius_km"))

    def options(types, kg):
        opts = [second_life_option(dict(load, quantity_kg=kg), o, crop, configs) for o in near if o["type"] in types]
        return sorted(opts, key=lambda o: SECOND_LIFE_ORDER.index(o["type"]))  # stable: nearest first within a type
    edible = options(EDIBLE_TYPES, split["edible_kg"]) if split["edible_kg"] > 0 else []
    top = edible[0] if edible else None
    to_recover = split["spoiled_kg"] + (0 if top else split["edible_kg"])
    recover_opts = options(RECOVER_TYPES, to_recover) if to_recover > 0 else []
    recover = recover_opts[0] if recover_opts else None
    return {
        "load_id": load.get("load_id"), "crop": crop["crop_id"], "quantity_kg": q, "split": split,
        "top": top, "recover": recover,
        "alternatives": [o for o in edible + recover_opts if o is not top and o is not recover],
        "impact": rescue_impact(split, top, recover, configs["assumptions"]),
    }


def allocate(loads, crops, market_ctx, outlets, configs):
    """Allocate loads largest first. crops/market_ctx are keyed by crop_id.

    Returns (results in input order, dA_kg {crop_id: {market_id: kg}}).
    """
    added = {c: {} for c in market_ctx}
    results = [None] * len(loads)
    for i in sorted(range(len(loads)), key=lambda i: -loads[i]["quantity_kg"]):
        c = loads[i]["crop"]
        results[i] = allocate_load(loads[i], crops[c], market_ctx[c], outlets, added[c], configs)
    return results, added

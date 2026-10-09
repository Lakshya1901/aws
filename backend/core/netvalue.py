"""Step 4: net value per kg for one load at one outlet (CLAUDE.md Section 9)."""
from math import asin, cos, radians, sin, sqrt

from .config import CoreError, assumption
from .pricing import price_on_arrival
from .risk import projected_ratio, risk_level
from .spoilage import spoilage_share


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = radians(lat1), radians(lat2)
    dp, dl = p2 - p1, radians(lon2 - lon1)
    return 2 * 6371.0 * asin(sqrt(sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2))


def route(origin, dest_id, dest, routes, assumptions):
    """(distance_km, drive_hours, distance_approx).

    Uses a routed {distance_km, drive_hours} from routes[dest_id] when supplied; otherwise
    haversine x road_factor (approx) and drive_hours = distance / truck_speed_kmph.
    """
    r = (routes or {}).get(dest_id) or {}
    if r.get("distance_km") is not None:
        distance, approx = r["distance_km"], False
    else:
        straight = haversine_km(origin["lat"], origin["lon"], dest["lat"], dest["lon"])
        distance, approx = straight * assumption(assumptions, "road_factor"), True
    hours = r.get("drive_hours")
    if hours is None:
        speed = assumption(assumptions, "truck_speed_kmph")
        if speed is None:
            raise CoreError("drive_time_unavailable",
                            "No routed drive time and truck_speed_kmph is not set in config/assumptions.json")
        hours = distance / speed
    return distance, hours, approx


def net_value(price, spoil, distance_km, freight_rate, deduct_pct):
    """net = P_hat*(1-s) - freight*distance/1000 - P_hat*deduct_pct, as {low, mid, high}.

    deduct_pct = fee_pct + commission_pct + handling_pct of the destination state.
    low pairs the low price with high spoilage; high pairs the high price with low spoilage.
    """
    freight = freight_rate * distance_km / 1000

    def n(p, s):
        return p * (1 - s) - freight - p * deduct_pct
    return {"low": n(price["low"], spoil["high"]), "mid": n(price["mid"], spoil["mid"]),
            "high": n(price["high"], spoil["low"])}


def fresh_option(load, mkt, added_kg, crop, configs):
    """Ranked-outlet dict for a reporting mandi. mkt = {"market", "risk", "fit"}; added_kg = dA already there."""
    a = configs["assumptions"]
    market, risk, fit = mkt["market"], mkt["risk"], mkt["fit"]
    state = market["state"]
    distance, hours, approx = route(load["origin"], market["market_id"], market, load.get("routes"), a)
    trip_h = load.get("hours_since_harvest", 0) + hours + assumption(a, "t_wait_h")
    spoil = spoilage_share(trip_h, load["temp_c"], crop)
    k = assumption(a, "stale_range_multiplier") if risk["stale"] else 1.0
    price = price_on_arrival(risk["price_kg"], risk["arrivals_t"], added_kg / 1000, fit["b"], fit["resid_sd"], k)
    fee, comm, hand = (assumption(a, key, state) for key in ("fee_pct", "commission_pct", "handling_pct"))
    freight_rate = assumption(a, "freight_rs_per_tonne_km")
    proj = projected_ratio(risk, (added_kg + load["quantity_kg"]) / 1000)
    return {
        "outlet_id": market["market_id"], "name": market.get("name"), "type": "mandi", "state": state,
        "net_rs_per_kg": net_value(price, spoil, distance, freight_rate, fee + comm + hand),
        "price_rs_per_kg": price,
        "distance_km": distance, "distance_approx": approx, "drive_hours": hours,
        "spoilage_share": spoil["mid"], "spoilage_range": spoil,
        "freight_rs_per_kg": freight_rate * distance / 1000,
        "freight_rs_load": freight_rate * distance / 1000 * load["quantity_kg"],
        "fee_pct": fee, "commission_pct": comm, "handling_pct": hand,
        "risk_level": risk["risk_level"], "arrival_ratio": risk["arrival_ratio"],
        "projected_arrival_ratio": proj,
        "projected_risk_level": risk_level(proj, risk["price_change_3d"], configs["model"]["risk"]),
        "price_change_3d": risk["price_change_3d"],
        "elasticity_b": fit["b"], "stale": risk["stale"], "latest_date": risk["latest_date"],
        "data_complete": risk["data_complete"],
    }


def second_life_option(load, outlet, crop, configs):
    """Processor: P_hat = offer_price_kg (null -> net null, 'not yet estimated'). Food bank, feed, biogas,
    compost: P_hat = 0.

    No mandi wait, fee, commission or handling applies at a second-life outlet. Rescue with a trader split may
    have no temperature (temp_c None): spoilage and net are then null, 'not yet estimated'.
    """
    a = configs["assumptions"]
    distance, hours, approx = route(load["origin"], outlet["outlet_id"], outlet, load.get("routes"), a)
    spoil = (None if load["temp_c"] is None
             else spoilage_share(load.get("hours_since_harvest", 0) + hours, load["temp_c"], crop))
    freight_rate = assumption(a, "freight_rs_per_tonne_km")
    p = outlet.get("offer_price_kg") if outlet["type"] == "processor" else 0.0
    net = (None if p is None or spoil is None
           else net_value({"low": p, "mid": p, "high": p}, spoil, distance, freight_rate, 0.0))
    return {
        "outlet_id": outlet["outlet_id"], "name": outlet.get("name"), "type": outlet["type"],
        "state": outlet.get("state"),
        "net_rs_per_kg": net, "net_note": "not yet estimated" if net is None else None,
        "distance_km": distance, "distance_approx": approx, "drive_hours": hours,
        "spoilage_share": None if spoil is None else spoil["mid"], "spoilage_range": spoil,
        "freight_rs_per_kg": freight_rate * distance / 1000,
        "freight_rs_load": freight_rate * distance / 1000 * load["quantity_kg"],
        "contact": outlet.get("contact"), "verified": outlet.get("verified"), "note": outlet.get("note"),
    }

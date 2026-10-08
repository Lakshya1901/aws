"""Step 6: waste avoided and resource accounting (CLAUDE.md Section 9). Null means 'not yet estimated', never 0."""
from .config import assumption


def dump_share_band(ratio, table):
    """Index of the u(R) band R falls in (r_below is the exclusive upper bound)."""
    for i, band in enumerate(table):
        if band["r_below"] is None or ratio < band["r_below"]:
            return i
    return len(table) - 1


def _loss_parts(option, table):
    """(spoilage range, u low/mid/high) for an outlet, or None when it can't be estimated.

    Mandi: u from the u(R) band of its projected ratio (low/high = band below/above).
    Processor and food bank: u = 0 (food still eaten). Feed/compost: loss 1 (no food recovered for people).
    """
    t = option["type"]
    if t == "feed_compost":
        return {"low": 1.0, "mid": 1.0, "high": 1.0}, {"low": 0.0, "mid": 0.0, "high": 0.0}
    if t in ("processor", "food_bank"):
        return option["spoilage_range"], {"low": 0.0, "mid": 0.0, "high": 0.0}
    if t != "mandi" or option.get("projected_arrival_ratio") is None:
        return None
    i = dump_share_band(option["projected_arrival_ratio"], table)
    u = {"low": table[max(i - 1, 0)]["u"], "mid": table[i]["u"], "high": table[min(i + 1, len(table) - 1)]["u"]}
    return option["spoilage_range"], u


def waste_avoided(quantity_kg, default, advised, assumptions):
    """W = Q * (L_default - L_advised), L = min(1, s + u(R)), as {low, mid, high} or None.

    low: default with the band below and low spoilage vs advised with high spoilage;
    high: default with the band above and high spoilage vs advised with low spoilage.
    """
    if advised["outlet_id"] == default["outlet_id"] and advised["type"] == default["type"]:
        return {"low": 0.0, "mid": 0.0, "high": 0.0}
    table = assumption(assumptions, "dump_share_table")
    d, a = _loss_parts(default, table), _loss_parts(advised, table)
    if d is None or a is None:
        return None
    (sd, ud), (sa, ua) = d, a

    def loss(s, u):
        return min(1.0, s + u)
    return {
        "low": quantity_kg * (loss(sd["low"], ud["low"]) - loss(sa["high"], ua["mid"])),
        "mid": quantity_kg * (loss(sd["mid"], ud["mid"]) - loss(sa["mid"], ua["mid"])),
        "high": quantity_kg * (loss(sd["high"], ud["high"]) - loss(sa["low"], ua["mid"])),
    }


def impact(quantity_kg, default, advised, crop, assumptions):
    """Impact Ledger entry for one load. waste_avoided_kg and redirected_kg are separate keys, always."""
    w = waste_avoided(quantity_kg, default, advised, assumptions)
    moved = not (advised["outlet_id"] == default["outlet_id"] and advised["type"] == default["type"])
    extra_km = None if advised.get("distance_km") is None else advised["distance_km"] - default["distance_km"]
    diesel = None if extra_km is None else extra_km * assumption(assumptions, "diesel_l_per_km")
    co2 = None if diesel is None else diesel * assumption(assumptions, "co2_kg_per_l_diesel")
    water = crop.get("water_l_per_kg")
    return {
        "redirected_kg": quantity_kg if moved else 0,
        "waste_avoided_kg": w,
        "extra_km": extra_km,
        "diesel_l": diesel,
        "co2_kg": co2,
        "water_l": None if w is None or water is None else w["mid"] * water,
    }


def total_impact(impacts):
    """Sum per-load impacts. A total is null if any load's value is null (never treated as 0)."""
    def total(key):
        vals = [i[key] for i in impacts]
        return None if any(v is None for v in vals) else sum(vals)
    ws = [i["waste_avoided_kg"] for i in impacts]
    w = None if any(x is None for x in ws) else {k: sum(x[k] for x in ws) for k in ("low", "mid", "high")}
    return {"redirected_kg": total("redirected_kg"), "waste_avoided_kg": w, "extra_km": total("extra_km"),
            "diesel_l": total("diesel_l"), "co2_kg": total("co2_kg"), "water_l": total("water_l")}

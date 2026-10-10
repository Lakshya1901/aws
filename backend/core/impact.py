"""Step 6: waste avoided and resource accounting (CLAUDE.md Section 9). Null means 'not yet estimated', never 0."""
from .config import assumption

EDIBLE_TYPES = ("processor", "food_bank")  # Second Life: food still eaten
RECOVER_TYPES = ("feed", "biogas", "compost")  # Recover rung, in food recovery hierarchy order (D19)


def dump_share_band(ratio, table):
    """Index of the u(R) band R falls in (r_below is the exclusive upper bound)."""
    for i, band in enumerate(table):
        if band["r_below"] is None or ratio < band["r_below"]:
            return i
    return len(table) - 1


def _loss_parts(option, table, price_only_ratio=None):
    """(spoilage range, u low/mid/high) for an outlet, or None when it can't be estimated.

    Mandi: u from the u(R) band of its projected ratio (low/high = band below/above); with live prices only
    (D34), the band of price_only_ratio for its price-only risk level.
    Processor and food bank: u = 0 (food still eaten). Feed, biogas, compost: loss 1 (no food recovered for people).
    """
    t = option["type"]
    if t in RECOVER_TYPES:
        return {"low": 1.0, "mid": 1.0, "high": 1.0}, {"low": 0.0, "mid": 0.0, "high": 0.0}
    if t in EDIBLE_TYPES:
        return option["spoilage_range"], {"low": 0.0, "mid": 0.0, "high": 0.0}
    ratio = option.get("projected_arrival_ratio")
    if t == "mandi" and option.get("price_only"):  # D34: no arrivals; the R band its price-only level stands for
        ratio = (price_only_ratio or {}).get(option.get("projected_risk_level"))
    if t != "mandi" or ratio is None:
        return None
    i = dump_share_band(ratio, table)
    u = {"low": table[max(i - 1, 0)]["u"], "mid": table[i]["u"], "high": table[min(i + 1, len(table) - 1)]["u"]}
    return option["spoilage_range"], u


def below_cost(default, harvest_cost_rs_per_kg):
    """D12: the default mandi's mid net value per kg is below the crop's harvest cost."""
    net = default.get("net_rs_per_kg")
    return (default["type"] == "mandi" and net is not None and harvest_cost_rs_per_kg is not None
            and net["mid"] < harvest_cost_rs_per_kg)


def waste_avoided(quantity_kg, default, advised, assumptions, harvest_cost_rs_per_kg=None):
    """W = Q * (L_default - L_advised), L = min(1, s + u(R)), as {low, mid, high} or None.

    low: default with the band below and low spoilage vs advised with high spoilage;
    high: default with the band above and high spoilage vs advised with low spoilage.
    Price-below-cost dump (D12): when below_cost(default), u_default = max(u(R), below_cost_dump_share)
    for each of low/mid/high. Default side only.
    """
    if advised["outlet_id"] == default["outlet_id"] and advised["type"] == default["type"]:
        return {"low": 0.0, "mid": 0.0, "high": 0.0}
    table = assumption(assumptions, "dump_share_table")
    por = assumption(assumptions, "price_only_ratio")
    d, a = _loss_parts(default, table, por), _loss_parts(advised, table, por)
    if d is None or a is None:
        return None
    (sd, ud), (sa, ua) = d, a
    if below_cost(default, harvest_cost_rs_per_kg):
        floor = assumption(assumptions, "below_cost_dump_share")
        ud = {k: max(ud[k], floor[k]) for k in ud}

    def loss(s, u):
        return min(1.0, s + u)
    return {
        "low": quantity_kg * (loss(sd["low"], ud["low"]) - loss(sa["high"], ua["mid"])),
        "mid": quantity_kg * (loss(sd["mid"], ud["mid"]) - loss(sa["mid"], ua["mid"])),
        "high": quantity_kg * (loss(sd["high"], ud["high"]) - loss(sa["low"], ua["mid"])),
    }


def _ledger(prevented, rescued_kg, recovered_kg, biogas_kg, assumptions):
    """Impact Ledger lines (CLAUDE.md Section 9 Step 6). Kept out of landfill = Prevented + Rescued + Recovered;
    redirected is never added. Biogas energy is 0 with no biogas, null while biogas_yield is unsourced."""
    y = assumption(assumptions, "biogas_yield")
    return {
        "kept_out_of_landfill_kg": None if prevented is None else
        {k: prevented[k] + rescued_kg + recovered_kg for k in ("low", "mid", "high")},
        "rescued_kg": rescued_kg,
        "recovered_kg": recovered_kg,
        "biogas_kg": biogas_kg,
        "biogas_energy": 0.0 if biogas_kg == 0 else (None if y is None else biogas_kg * y),
        "biogas_energy_unit": assumptions["biogas_yield"].get("energy_unit"),
    }


def _routed(option):
    """True when the option is a real outlet (not the no-outlet fallback or hold)."""
    return option is not None and option.get("outlet_id") is not None


def impact(quantity_kg, default, advised, crop, assumptions):
    """Impact Ledger entry for one Prevent load. waste_avoided_kg and redirected_kg are separate keys, always."""
    w = waste_avoided(quantity_kg, default, advised, assumptions, crop.get("harvest_cost_rs_per_kg"))
    moved = not (advised["outlet_id"] == default["outlet_id"] and advised["type"] == default["type"])
    extra_km = None if advised.get("distance_km") is None else advised["distance_km"] - default["distance_km"]
    diesel = None if extra_km is None else extra_km * assumption(assumptions, "diesel_l_per_km")
    co2 = None if diesel is None else diesel * assumption(assumptions, "co2_kg_per_l_diesel")
    water = crop.get("water_l_per_kg")
    recovered = quantity_kg if advised["type"] in RECOVER_TYPES and _routed(advised) else 0
    return {
        **_ledger(w, 0, recovered, recovered if advised["type"] == "biogas" else 0, assumptions),
        "redirected_kg": quantity_kg if moved else 0,
        "waste_avoided_kg": w,
        "extra_km": extra_km,
        "diesel_l": diesel,
        "co2_kg": co2,
        "water_l": None if w is None or water is None else w["mid"] * water,
    }


def rescue_impact(split, edible_outlet, recover_outlet, assumptions):
    """Impact Ledger entry for Rescue (Step 5b). Edible kg with no processor or food bank go to the Recover rung.

    Nothing here is prevented or redirected; kg with no outlet in radius are neither rescued nor recovered.
    Rescue has no default market, so extra km, diesel, CO2 and water are 0 (not applicable), not unknown.
    """
    rescued = split["edible_kg"] if _routed(edible_outlet) else 0
    to_recover = split["spoiled_kg"] + split["edible_kg"] - rescued
    recovered = to_recover if _routed(recover_outlet) else 0
    zero = {"low": 0.0, "mid": 0.0, "high": 0.0}
    return {
        **_ledger(zero, rescued, recovered, recovered if recovered and recover_outlet["type"] == "biogas" else 0,
                  assumptions),
        "redirected_kg": 0, "waste_avoided_kg": zero,
        # No default market to compare with, so no extra distance; 0 keeps session totals summable.
        "extra_km": 0.0, "diesel_l": 0.0, "co2_kg": 0.0, "water_l": 0.0,
    }


def total_impact(impacts):
    """Sum per-load impacts. A total is null if any load's value is null (never treated as 0)."""
    def total(key):
        vals = [i[key] for i in impacts]
        return None if any(v is None for v in vals) else sum(vals)
    def total_range(key):
        xs = [i[key] for i in impacts]
        return None if any(x is None for x in xs) else {k: sum(x[k] for x in xs) for k in ("low", "mid", "high")}
    units = {i["biogas_energy_unit"] for i in impacts}
    return {"kept_out_of_landfill_kg": total_range("kept_out_of_landfill_kg"),
            "rescued_kg": total("rescued_kg"), "recovered_kg": total("recovered_kg"),
            "biogas_kg": total("biogas_kg"), "biogas_energy": total("biogas_energy"),
            "biogas_energy_unit": units.pop() if len(units) == 1 else None,
            "redirected_kg": total("redirected_kg"), "waste_avoided_kg": total_range("waste_avoided_kg"),
            "extra_km": total("extra_km"),
            "diesel_l": total("diesel_l"), "co2_kg": total("co2_kg"), "water_l": total("water_l")}

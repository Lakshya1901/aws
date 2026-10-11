"""One-farm replay of March-May 2026 (the case study report), with the same engine and data as simulate_2026.py.

A simulated 8-acre vegetable farm near Narela, north-west Delhi (28.840, 77.060): tomato (3 acres, 1,300 kg every
second day), bottle gourd (2 acres, 1,000 kg every third day), cauliflower (1 acre, 1,500 kg every third day in
March) and okra (2 acres from 15 April, 800 kg every second day); once a week 300 kg of tomato comes back unsold
from Azadpur (one day old). Quantities are rough yields for the area, not one grower's records.
Each picking day's loads go through the advisor's /plan together; unsold lots through /recommend (Rescue).

Usage: python analysis/simulate_farm_2026.py --raw DIR --snapshot DIR [--out FILE]
Writes analysis/out/farm_2026.json in the simulate_2026.py layout (region "Narela farm"); summarise with
analysis/sim_summary.py --prefix farm_2026.
"""
import argparse
import os
import pathlib
import sys
from datetime import date, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.simulate_2026 import build_snapshot, classify, prices, realised  # noqa: E402

FARM = {"lat": 28.840, "lon": 77.060, "place": "Narela"}
AZADPUR = {"lat": 28.721, "lon": 77.165, "place": "Azadpur"}
CROPS = ["tomato", "bottle_gourd", "cauliflower", "bhindi_ladies_finger"]
# crop, kg per picking, every n days, first day, last day
PICKING = [("tomato", 1300, 2, "2026-03-01", "2026-05-31"),
           ("bottle_gourd", 1000, 3, "2026-03-01", "2026-05-31"),
           ("cauliflower", 1500, 3, "2026-03-01", "2026-03-31"),
           ("bhindi_ladies_finger", 800, 2, "2026-04-15", "2026-05-31")]
UNSOLD = ("tomato", 300, 1, 7)  # crop, kg, days since harvest, every n days
REGION = "Narela farm"


def picks(d):
    out = []
    for crop, kg, every, first, last in PICKING:
        if first <= d.isoformat() <= last and (d - date.fromisoformat(first)).days % every == 0:
            out.append((crop, kg))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", type=pathlib.Path, required=True)
    p.add_argument("--snapshot", type=pathlib.Path, required=True)
    p.add_argument("--start", default="2026-03-01")
    p.add_argument("--end", default="2026-05-31")
    p.add_argument("--out", type=pathlib.Path, default=ROOT / "analysis" / "out" / "farm_2026.json")
    a = p.parse_args()
    build_snapshot(a.raw, a.snapshot, a.start, a.end, CROPS)
    os.environ.update(DATA_SOURCE="snapshot", SNAPSHOT_DIR=str(a.snapshot))
    os.environ.pop("WEATHER_LIVE", None)
    from backend.adapters import store
    from backend.handlers import advisor
    import json
    cfg = store.configs()
    freight = cfg["assumptions"]["freight_rs_per_tonne_km"]["value"]
    series = prices(a.snapshot, CROPS)
    loads_out, rescues, errors = [], [], []
    day = date.fromisoformat(a.start)
    while day.isoformat() <= a.end:
        d = day.isoformat()
        os.environ["REPLAY_DATE"] = d
        specs = picks(day)
        if specs:
            body = {"language": "en", "plan_id": f"farm_{d}", "loads": [
                {"load_id": f"F{i}", "crop": c, "quantity_kg": q, "origin": FARM, "harvest": "today"}
                for i, (c, q) in enumerate(specs)]}
            try:
                res = advisor.post_plan(body)
                for al in res["allocations"]:
                    top, dft, imp = al["outlet"], al["default"], al["impact"]
                    row = {"date": d, "region": REGION, "crop": al["crop"], "kg": al["quantity_kg"],
                           "default": dft and dft.get("name"), "default_level": dft and dft.get("risk_level"),
                           "default_ratio": dft and dft.get("arrival_ratio"), "default_dp": dft and dft.get("price_change_3d"),
                           "advised": top and (top.get("name") or top["outlet_id"]), "advised_type": top and top["type"],
                           "diverted": bool(top and dft and top["outlet_id"] != dft["outlet_id"]),
                           "problem": classify(dft, cfg["crops"][al["crop"]].get("harvest_cost_rs_per_kg")),
                           "advice": al["advice"], "waste_avoided": imp["waste_avoided_kg"],
                           "money_saved": imp.get("money_saved_rs"), "extra_km": imp["extra_km"],
                           "stale": bool(top and top.get("stale"))}
                    if row["diverted"] and top["type"] == "mandi":
                        ra = realised(series.get((top["outlet_id"], al["crop"])), d)
                        rd = realised(series.get((dft["outlet_id"], al["crop"])), d)
                        if ra and rd:
                            row["realised_gap_rs_kg"] = round((ra[1] - freight * top["distance_km"] / 1000)
                                                              - (rd[1] - freight * dft["distance_km"] / 1000), 2)
                            row["predicted_gap_rs_kg"] = round(top["net_rs_per_kg"]["mid"] - dft["net_rs_per_kg"]["mid"], 2)
                    loads_out.append(row)
            except Exception as e:  # noqa: BLE001 - record and go on
                errors.append({"date": d, "region": REGION, "error": getattr(e, "code", type(e).__name__)})
        crop, kg, days, every = UNSOLD
        if (day - date(2026, 3, 1)).days % every == every - 1:
            try:
                r = advisor.post_recommend({"source": "mandi_unsold", "crop": crop, "quantity_kg": kg,
                                            "days_since_harvest": days, "origin": AZADPUR, "language": "en",
                                            "plan_id": f"farm_rescue_{d}"})
                dest = r["top"] or r["recover"]
                rescues.append({"date": d, "edible_kg": r["split"]["edible_kg"], "spoiled_kg": r["split"]["spoiled_kg"],
                                "to": dest and (dest.get("name") or dest["outlet_id"]), "to_type": dest and dest["type"],
                                "rescued_kg": r["impact"]["rescued_kg"], "recovered_kg": r["impact"]["recovered_kg"]})
            except Exception as e:  # noqa: BLE001
                errors.append({"date": d, "region": REGION + " unsold", "error": getattr(e, "code", type(e).__name__)})
        day += timedelta(days=1)
    a.out.write_text(json.dumps({"window": [a.start, a.end], "origins": {REGION: FARM}, "loads": loads_out,
                                 "rescues": rescues, "errors": errors}, indent=1, sort_keys=True))
    print(f"{len(loads_out)} loads, {len(rescues)} unsold lots, {len(errors)} errors -> {a.out}")


if __name__ == "__main__":
    main()

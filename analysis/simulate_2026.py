"""Three-month replay of the deployed engine on 2026 data (March-May 2026, the latest market-level data).

Every day from --start to --end, the advisor's own /plan and /recommend code (snapshot mode, REPLAY_DATE = that day)
routes the same simulated daily loads, as an FPO would send them:
- Kolar tomato belt: the ten demo loads (16 t of tomato, D9) from Kolar (13.137, 78.134), routes cached.
- Delhi: five 5 t loads (tomato, onion, banana, cabbage, cauliflower) from Azadpur (28.721, 77.165), plus one
  unsold lot at Azadpur (2 t tomato, harvested yesterday; Rescue, Step 5b).
Inputs: market-level AGMARKNET history per crop from s3://annasetu-data-<suffix>/idp/<crop>.csv.gz (India Data
Portal, D24; download with `aws s3 cp`), cut here to markets within 350 km of either origin; NASA POWER hourly
temperature at both origins (D16), fetched once and cached in the snapshot directory.

Per load it records the nearest mandi (default) and its risk, the advised outlet, waste avoided, money saved and
extra km (all engine output), and classifies the default market's day (Section 9 Step 1 levels, D12):
arrival glut / arrival watch / price fall (price-only watch or glut) / below harvest cost / normal / no data.
Verification (out of sample): for each load sent away from the nearest mandi, the realised modal price at the
advised and the default market on their next report after the day (1-7 days later), freight-adjusted with the
same Rs per tonne-km; fees, commission and spoilage are left out (they are close to proportional on both sides).

Usage: python analysis/simulate_2026.py --raw DIR --snapshot DIR [--start 2026-03-01 --end 2026-05-31]
Writes analysis/out/sim_2026.json (deterministic for the same inputs).
"""
import argparse
import csv
import gzip
import json
import math
import os
import pathlib
import sys
from datetime import date, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CROPS = ["tomato", "onion", "banana", "cabbage", "cauliflower"]
KOLAR = {"lat": 13.137, "lon": 78.134, "place": "Kolar"}
AZADPUR = {"lat": 28.721, "lon": 77.165, "place": "Azadpur"}
KOLAR_QTY = [3000, 2500, 2000, 2000, 1500, 1500, 1200, 1000, 800, 500]
DELHI_LOADS = [(c, 5000) for c in CROPS]
RESCUE = ("tomato", 2000, 1)
RADIUS_KM = 350
DATA_END = "2026-05-31"  # last day in the India Data Portal files (D24)


def km(a_lat, a_lon, b_lat, b_lon):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b_lon - a_lon) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def build_snapshot(raw, out, start, end):
    """Cut each crop's national file to markets near either origin; cache NASA POWER temperature at both."""
    markets = {m["market_id"]: m for m in json.loads((ROOT / "config/markets.json").read_text())["markets"]
               if m.get("lat") is not None}
    near = {i for i, m in markets.items()
            if min(km(o["lat"], o["lon"], m["lat"], m["lon"]) for o in (KOLAR, AZADPUR)) <= RADIUS_KM}
    out.mkdir(parents=True, exist_ok=True)
    for crop in CROPS:
        dst = out / f"sim_{crop}_2021-01-01_{DATA_END}.csv.gz"
        if dst.exists():
            continue
        with gzip.open(raw / f"{crop}.csv.gz", "rt", newline="") as src, gzip.open(dst, "wt", newline="") as fh:
            r = csv.DictReader(src)
            w = csv.DictWriter(fh, r.fieldnames)
            w.writeheader()
            w.writerows(row for row in r if row["market_id"] in near and row["date"] <= DATA_END)
    wf = out / f"weather_power_sim_{start}_{end}.json"
    if not wf.exists():
        from backend.adapters.weather import fetch_hourly_power
        pts = {n: dict(o, **fetch_hourly_power(o["lat"], o["lon"], start, end)) for n, o in
               (("kolar", KOLAR), ("azadpur", AZADPUR))}
        wf.write_text(json.dumps({"source": "NASA POWER hourly (MERRA-2), https://power.larc.nasa.gov",
                                  "timezone": "local solar time", "from": start, "to": end,
                                  "markets": {n: {k: p[k] for k in ("lat", "lon", "source_url", "time",
                                                                    "temperature_c")} for n, p in pts.items()}}))


def prices(snapshot):
    """{(market_id, crop): [(date, modal Rs/kg)]} sorted by date, for the realised-price check."""
    out = {}
    for crop in CROPS:
        f = next(snapshot.glob(f"sim_{crop}_*.csv.gz"))
        with gzip.open(f, "rt", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["modal_price_kg"]:
                    out.setdefault((r["market_id"], crop), []).append((r["date"], float(r["modal_price_kg"])))
    for v in out.values():
        v.sort()
    return out


def realised(series, day):
    """First report after `day`, within 7 days: (date, price) or None."""
    last = (date.fromisoformat(day) + timedelta(days=7)).isoformat()
    return next(((d, p) for d, p in series or [] if day < d <= last), None)


def classify(o, harvest_cost):
    """The default (nearest) market's problem on the day."""
    if o is None or o.get("risk_level") is None:
        return "no_data"
    r, dp, lvl = o.get("arrival_ratio"), o.get("price_change_3d"), o["risk_level"]
    if lvl == "glut" and r is not None and r >= 1.5:
        return "arrival_glut"
    if lvl == "watch" and r is not None and r >= 1.3:
        return "arrival_watch"
    if lvl in ("watch", "glut"):
        return "price_fall"
    mid = (o.get("net_rs_per_kg") or {}).get("mid")
    if harvest_cost and mid is not None and mid < harvest_cost:
        return "below_cost"
    return "normal"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", type=pathlib.Path, required=True)
    p.add_argument("--snapshot", type=pathlib.Path, required=True)
    p.add_argument("--start", default="2026-03-01")
    p.add_argument("--end", default="2026-05-31")
    p.add_argument("--out", type=pathlib.Path, default=ROOT / "analysis" / "out" / "sim_2026.json")
    a = p.parse_args()
    build_snapshot(a.raw, a.snapshot, a.start, a.end)
    os.environ.update(DATA_SOURCE="snapshot", SNAPSHOT_DIR=str(a.snapshot))
    os.environ.pop("WEATHER_LIVE", None)
    from backend.adapters import store
    from backend.handlers import advisor
    cfg = store.configs()
    freight = cfg["assumptions"]["freight_rs_per_tonne_km"]["value"]
    series = prices(a.snapshot)

    loads_out, rescues, errors = [], [], []
    day = date.fromisoformat(a.start)
    while day.isoformat() <= a.end:
        d = day.isoformat()
        os.environ["REPLAY_DATE"] = d
        for region, origin, specs in (("Kolar", KOLAR, [("tomato", q) for q in KOLAR_QTY]),
                                      ("Delhi", AZADPUR, DELHI_LOADS)):
            body = {"language": "en", "plan_id": f"sim_{region}_{d}", "loads": [
                {"load_id": f"{region}{i}", "crop": c, "quantity_kg": q, "origin": origin, "harvest": "today"}
                for i, (c, q) in enumerate(specs)]}
            try:
                res = advisor.post_plan(body)
            except Exception as e:  # noqa: BLE001 - record and go on; the count is reported
                errors.append({"date": d, "region": region, "error": getattr(e, "code", type(e).__name__)})
                continue
            for al in res["allocations"]:
                top, dft, imp = al["outlet"], al["default"], al["impact"]
                hc = cfg["crops"][al["crop"]].get("harvest_cost_rs_per_kg")
                row = {"date": d, "region": region, "crop": al["crop"], "kg": al["quantity_kg"],
                       "default": dft and dft.get("name"), "default_id": dft and dft["outlet_id"],
                       "default_level": dft and dft.get("risk_level"), "default_ratio": dft and dft.get("arrival_ratio"),
                       "default_dp": dft and dft.get("price_change_3d"),
                       "advised": top and (top.get("name") or top["outlet_id"]), "advised_id": top and top["outlet_id"],
                       "advised_type": top and top["type"],
                       "diverted": bool(top and dft and top["outlet_id"] != dft["outlet_id"]),
                       "problem": classify(dft, hc), "advice": al["advice"],
                       "waste_avoided": imp["waste_avoided_kg"], "money_saved": imp.get("money_saved_rs"),
                       "extra_km": imp["extra_km"], "stale": bool(top and top.get("stale"))}
                if row["diverted"] and top["type"] == "mandi":
                    ra = realised(series.get((top["outlet_id"], al["crop"])), d)
                    rd = realised(series.get((dft["outlet_id"], al["crop"])), d)
                    if ra and rd:
                        gap = (ra[1] - freight * top["distance_km"] / 1000) - (rd[1] - freight * dft["distance_km"] / 1000)
                        row["realised_gap_rs_kg"] = round(gap, 2)
                        row["predicted_gap_rs_kg"] = round(top["net_rs_per_kg"]["mid"] - dft["net_rs_per_kg"]["mid"], 2)
                loads_out.append(row)
        c, q, days = RESCUE
        try:
            r = advisor.post_recommend({"source": "mandi_unsold", "crop": c, "quantity_kg": q,
                                        "days_since_harvest": days, "origin": AZADPUR, "language": "en",
                                        "plan_id": f"sim_rescue_{d}"})
            dest = r["top"] or r["recover"]
            rescues.append({"date": d, "edible_kg": r["split"]["edible_kg"], "spoiled_kg": r["split"]["spoiled_kg"],
                            "to": dest and (dest.get("name") or dest["outlet_id"]), "to_type": dest and dest["type"],
                            "rescued_kg": r["impact"]["rescued_kg"], "recovered_kg": r["impact"]["recovered_kg"]})
        except Exception as e:  # noqa: BLE001
            errors.append({"date": d, "region": "Delhi rescue", "error": getattr(e, "code", type(e).__name__)})
        day += timedelta(days=1)

    out = a.out
    out.write_text(json.dumps({"window": [a.start, a.end], "origins": {"Kolar": KOLAR, "Delhi": AZADPUR},
                               "loads": loads_out, "rescues": rescues, "errors": errors}, indent=1, sort_keys=True))
    print(f"{len(loads_out)} loads, {len(rescues)} unsold lots, {len(errors)} errors -> {out}")


if __name__ == "__main__":
    main()

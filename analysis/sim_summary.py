"""Merge simulate_2026.py runs and compute the figures for the 2026 stat report.

Usage: python analysis/sim_summary.py [--prefix sim_2026] PART.json [PART.json ...]
Writes analysis/out/sim_2026.json (all loads, unsold lots and errors, merged by date) and
analysis/out/sim_2026_summary.json (the report's figures). Sums use each load's mid estimate; waste avoided is
given both as the signed sum (loads whose longer trip spoils more count negative) and as the count of loads with
a positive value. Verification uses only loads sent to another mandi with a report at both markets in the next
7 days (simulate_2026.py).
"""
import json
import pathlib
import statistics
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLASSES = ["arrival_glut", "arrival_watch", "price_fall", "below_cost", "normal", "no_data"]


def mid(r):
    return (r or {}).get("mid") or 0.0


def rng(rows, key):
    return {k: round(sum((r[key] or {}).get(k) or 0.0 for r in rows)) for k in ("low", "mid", "high")}


def main(parts, prefix="sim_2026"):
    loads, rescues, errors, window = [], [], [], []
    for p in parts:
        d = json.loads(pathlib.Path(p).read_text())
        loads += d["loads"]
        rescues += d["rescues"]
        errors += d["errors"]
        window += d["window"]
    loads.sort(key=lambda r: (r["date"], r["region"], r["crop"], -r["kg"]))
    rescues.sort(key=lambda r: r["date"])
    window = [min(window), max(window)]
    out = ROOT / "analysis" / "out"
    (out / f"{prefix}.json").write_text(json.dumps({"window": window, "loads": loads, "rescues": rescues,
                                                   "errors": errors}, sort_keys=True))

    def block(rows):
        div = [r for r in rows if r["diverted"]]
        ver = [r for r in rows if "realised_gap_rs_kg" in r]
        return {
            "loads": len(rows), "kg": sum(r["kg"] for r in rows), "days": len({r["date"] for r in rows}),
            "diverted": len(div), "diverted_kg": sum(r["kg"] for r in div),
            "to_second_life": sum(r["advised_type"] != "mandi" for r in rows),
            "advice": dict(Counter(r["advice"] for r in rows if r["advice"])),
            "waste_avoided_kg": rng(rows, "waste_avoided"),
            "loads_waste_positive": sum(mid(r["waste_avoided"]) > 0 for r in rows),
            "money_saved_rs": rng(rows, "money_saved"),
            "extra_km": round(sum(r["extra_km"] or 0 for r in rows)),
            "problems": {c: sum(r["problem"] == c for r in rows) for c in CLASSES},
            "stale_top": sum(r["stale"] for r in rows),
            "verified": len(ver),
            "verified_hit": sum(r["realised_gap_rs_kg"] > 0 for r in ver),
            "realised_gap_median": round(statistics.median([r["realised_gap_rs_kg"] for r in ver]), 2) if ver else None,
            "predicted_gap_median": round(statistics.median([r["predicted_gap_rs_kg"] for r in ver]), 2) if ver else None,
        }

    regions = sorted({r["region"] for r in loads})
    daily = defaultdict(lambda: {r: {"waste": 0.0, "money": 0.0, "glut_watch": 0} for r in regions})
    for r in loads:
        x = daily[r["date"]][r["region"]]
        x["waste"] += mid(r["waste_avoided"])
        x["money"] += mid(r["money_saved"])
        x["glut_watch"] += r["default_level"] in ("watch", "glut")
    summary = {
        "window": window, "errors": len(errors),
        "all": block(loads), "by_region": {g: block([r for r in loads if r["region"] == g]) for g in regions},
        "by_crop": {f"{g}/{c}": block([r for r in loads if r["region"] == g and r["crop"] == c])
                    for g, c in sorted({(r["region"], r["crop"]) for r in loads})},
        "rescue": {"lots": len(rescues), "kg": round(sum(r["edible_kg"] + r["spoiled_kg"] for r in rescues)),
                   "rescued_kg": round(sum(r["rescued_kg"] for r in rescues)),
                   "recovered_kg": round(sum(r["recovered_kg"] for r in rescues)),
                   "to": dict(Counter(r["to"] for r in rescues))},
        "daily": [{"date": d, **{g: {k: round(v) for k, v in daily[d][g].items()} for g in regions}}
                  for d in sorted(daily)],
        "verification_points": [[r["predicted_gap_rs_kg"], r["realised_gap_rs_kg"], r["region"]]
                                for r in loads if "realised_gap_rs_kg" in r],
    }
    (out / f"{prefix}_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    a = summary["all"]
    print(f"{a['loads']} loads, {a['diverted']} diverted, waste avoided {a['waste_avoided_kg']}, "
          f"money {a['money_saved_rs']}, verified {a['verified_hit']}/{a['verified']}, errors {len(errors)}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--prefix"]:
        main(args[2:], args[1])
    else:
        main(args)

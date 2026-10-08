"""Rebuild data/snapshot/ceda_<crop>_<from>_<to>.csv from CEDA for every market in config/markets.json.

Usage: python scripts/build_snapshot.py tomato 2022-01-01 2025-06-30
"""
import csv
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.adapters import ceda  # noqa: E402

FIELDS = ["date", "market_id", "crop", "arrivals_t", "min_price_kg", "max_price_kg", "modal_price_kg", "source"]


def main(crop, start, end):
    markets = json.loads((ROOT / "config/markets.json").read_text())["markets"]
    rows, manifest = [], {"source": ceda.BASE, "crop": crop, "from": start, "to": end,
                          "pulled_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                          "units": {"price": "Rs/quintal in source, Rs/kg in snapshot", "arrivals": "tonnes"},
                          "level": "district aggregate", "markets": {}}
    for m in markets:
        raw = ceda.fetch_raw(crop, m["ceda"]["state_id"], m["ceda"]["district_id"], start, end)
        got = ceda.normalise(raw, m["market_id"], crop)
        rows += got
        manifest["markets"][m["market_id"]] = {
            "rows": len(got),
            "price_days": sum(r["modal_price_kg"] is not None for r in got),
            "arrival_days": sum(r["arrivals_t"] is not None for r in got),
            "raw_sha256": hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()}
        print(m["market_id"], manifest["markets"][m["market_id"]], flush=True)
    out = ROOT / f"data/snapshot/ceda_{crop}_{start}_{end}.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    manifest["csv_sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:4])

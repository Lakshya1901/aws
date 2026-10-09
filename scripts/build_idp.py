"""Split the India Data Portal AGMARKNET bulk CSVs into one market-level file per commodity (CLAUDE.md D24).

Sources (Open Data Commons Attribution License; Ministry of Agriculture & Farmers Welfare via agmarknet.gov.in):
  https://ckandev.indiadataportal.com/dataset/agriculture-marketing
  "APMC Arrivals And Prices (Old Source)"  2021-01-01..2025-10-26
  "APMC Arrivals And Prices (New Source)"  2025-10-27..2026-05-31

Only rows with arrivals in tonnes and prices in Rs/quintal are kept (bundle- and unit-priced rows are dropped,
never converted). Varieties are aggregated per market-day (Section 8.2): arrivals summed, modal price weighted by
arrivals (plain mean when no arrivals), min of min, max of max. Prices become Rs/kg.

market_id = "<census state code>-<normalised market name>", so a market keeps its history across the two sources.
crop_id   = normalised commodity name (case, spaces and punctuation folded).

Outputs in --out:
  <crop_id>.csv.gz      date, market_id, crop, arrivals_t, min/max/modal_price_kg, source (snapshot schema)
  markets_raw.json      every market with the coordinates each source gives
  commodities.json      crop_id, name, category, markets, rows, from, to
  manifest.json         input sizes and sha256, row counts, dropped rows by reason

Usage: python scripts/build_idp.py --old old.csv --new new.csv --out <dir>
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
import re

COLS = {
    "old": {"date": "report_date", "market": "market_center", "aunit": "arrivals_unit", "category": "commodity_type"},
    "new": {"date": "date", "market": "market_center_name", "aunit": "arrival_units", "category": None},
}
TONNES = {"Tonnes", "Metric Tonnes"}
QUINTAL = {"Rs/Quintal", "Rs./Quintal"}
FIELDS = ["date", "market_id", "crop", "arrivals_t", "min_price_kg", "max_price_kg", "modal_price_kg", "source"]
MARKET_SUFFIX = re.compile(r"\b(apmc|f and v|f&v)\b", re.I)
# Official city renames between the two sources, so a market keeps one id (market names only, never commodities).
RENAMES = {"bangalore": "bengaluru", "mysore": "mysuru", "belgaum": "belagavi", "gulbarga": "kalaburagi",
           "bellary": "ballari", "shimoga": "shivamogga", "tumkur": "tumakuru", "hubli": "hubballi",
           "bijapur": "vijayapura", "gurgaon": "gurugram", "allahabad": "prayagraj", "trivandrum": "thiruvananthapuram",
           "calicut": "kozhikode", "cochin": "kochi", "baroda": "vadodara", "poona": "pune", "madras": "chennai"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def market_name(s):
    return re.sub(r"\s+", " ", re.sub(r"\(\s*\)", "", MARKET_SUFFIX.sub("", s))).strip(" -(,") or s


def market_id(state_code, name):
    words = [RENAMES.get(w, w) for w in slug(market_name(name)).split("_")]
    return f"{int(state_code)}-{''.join(words)}"


def num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def split(paths, tmp):
    """Pass 1: normalised rows into one temp CSV per commodity; market and commodity catalogues."""
    handles, markets, commodities, dropped = {}, {}, {}, {}
    for kind, path in paths:
        c = COLS[kind]
        with open(path, newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                if r[c["aunit"]] not in TONNES or r["price_unit"] not in QUINTAL:
                    dropped["unit"] = dropped.get("unit", 0) + 1
                    continue
                modal, arr = num(r["modal_price"]), num(r["arrival_quantity"])
                if not modal or modal <= 0 or (arr is not None and arr < 0) or not r["state_code"].isdigit():
                    dropped["invalid"] = dropped.get("invalid", 0) + 1
                    continue
                crop = slug(r["commodity_name"])
                mid = market_id(r["state_code"], r[c["market"]])
                m = markets.setdefault(mid, {"market_id": mid, "name": market_name(r[c["market"]]),
                                             "district": r["district_name"], "state_name": r["state_name"],
                                             "state_code": int(r["state_code"]), "coords": {}})
                m["coords"].setdefault(kind, (num(r["latitude"]), num(r["longitude"])))
                if kind == "new":
                    m["district"] = r["district_name"]
                d = r[c["date"]]
                k = commodities.setdefault(crop, {"crop_id": crop, "names": {}, "category": None, "markets": set(),
                                                  "rows": 0, "from": d, "to": d})
                k["names"][r["commodity_name"]] = d
                if c["category"] and r[c["category"]]:
                    k["category"] = r[c["category"]]
                k["markets"].add(mid)
                k["rows"] += 1
                k["from"], k["to"] = min(k["from"], d), max(k["to"], d)
                if crop not in handles:
                    handles[crop] = open(os.path.join(tmp, f"{crop}.csv"), "w", newline="", encoding="utf-8")
                csv.writer(handles[crop]).writerow([d, mid, arr if arr is not None else "", r["min_price"],
                                                    r["max_price"], modal, kind])
    for h in handles.values():
        h.close()
    return markets, commodities, dropped


def aggregate(tmp_file, crop, out_file):
    """Pass 2: one row per market-day (varieties aggregated), Rs/kg, written sorted and gzipped."""
    days = {}
    with open(tmp_file, newline="", encoding="utf-8") as fh:
        for d, mid, arr, lo, hi, modal, kind in csv.reader(fh):
            a = days.setdefault((mid, d), [0.0, 0.0, 0.0, 0, None, None, kind, False])
            modal, lo, hi = float(modal), num(lo), num(hi)
            if arr != "" and float(arr) > 0:
                a[0] += float(arr)
                a[1] += float(arr) * modal
                a[7] = True
            a[2] += modal
            a[3] += 1
            a[4] = lo if a[4] is None or (lo is not None and lo < a[4]) else a[4]
            a[5] = hi if a[5] is None or (hi is not None and hi > a[5]) else a[5]
    with gzip.open(out_file, "wt", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(FIELDS)
        for (mid, d) in sorted(days):
            arr, wsum, msum, n, lo, hi, kind, has_arr = days[(mid, d)]
            modal = wsum / arr if has_arr else msum / n
            w.writerow([d, mid, crop, round(arr, 4) if has_arr else "",
                        "" if lo is None else round(lo / 100, 4), "" if hi is None else round(hi / 100, 4),
                        round(modal / 100, 4), f"idp_agmarknet_{kind}"])
    return len(days)


def main(old, new, out):
    os.makedirs(out, exist_ok=True)
    tmp = os.path.join(out, "_tmp")
    os.makedirs(tmp, exist_ok=True)
    markets, commodities, dropped = split([("old", old), ("new", new)], tmp)
    for crop, k in sorted(commodities.items()):
        k["market_days"] = aggregate(os.path.join(tmp, f"{crop}.csv"), crop, os.path.join(out, f"{crop}.csv.gz"))
        os.remove(os.path.join(tmp, f"{crop}.csv"))
        k["name"] = max(k.pop("names").items(), key=lambda x: x[1])[0]  # latest name used in the source
        k["markets"] = len(k["markets"])
    os.rmdir(tmp)
    with open(os.path.join(out, "markets_raw.json"), "w", encoding="utf-8") as fh:
        json.dump(sorted(markets.values(), key=lambda m: m["market_id"]), fh, ensure_ascii=False)
    with open(os.path.join(out, "commodities.json"), "w", encoding="utf-8") as fh:
        json.dump(sorted(commodities.values(), key=lambda k: -k["markets"]), fh, ensure_ascii=False, indent=0)
    manifest = {"source": "https://ckandev.indiadataportal.com/dataset/agriculture-marketing",
                "license": "Open Data Commons Attribution License",
                "inputs": {os.path.basename(p): {"bytes": os.path.getsize(p), "sha256": sha256(p)} for p in (old, new)},
                "dropped_rows": dropped, "markets": len(markets), "commodities": len(commodities),
                "units": {"arrivals": "tonnes", "price": "Rs/quintal in source, Rs/kg in output"}}
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    print(json.dumps({k: v for k, v in manifest.items() if k != "inputs"}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    main(a.old, a.new, a.out)

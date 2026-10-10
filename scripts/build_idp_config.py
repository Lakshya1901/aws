"""config/markets.json and config/commodities.json from the scripts/build_idp.py output (CLAUDE.md D24).

Markets: coordinates come from the source data (CLAUDE.md Section 8.3 otherwise geocodes every market).
  - both sources in India and within AGREE_KM of each other, or only one source in India: that coordinate
    (new source preferred), coord_confidence "high";
  - sources disagree: Amazon Location place search "<market>, <district>, <state>, India", then without the
    district (districts renamed or split since 2011 confuse the geocoder). The first source coordinate within
    AGREE_KM of a hit with relevance >= MIN_RELEVANCE wins; if no hit confirms either, coord_confidence "low";
  - neither source in India: the first confident hit, else "low". Low = left out of routing until fixed.
Commodities: every commodity, with preload = the top N fruits and vegetables by number of reporting markets.
Snapshot (--snapshot-crops): data/snapshot/idp_<crop>_<from>_<to>.csv.gz for the markets within --snapshot-radius km
of --snapshot-origin, so the demo replays run offline (CLAUDE.md Section 20).

Usage: python scripts/build_idp_config.py --idp <dir> --index <PlaceIndexName> [--top 50] [--dry-run]
         [--snapshot-crops tomato,onion --snapshot-origin 13.137,78.134 --snapshot-radius 350]
"""
import argparse
import csv
import gzip
import io
import json
import math
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
AGREE_KM = 15
MIN_RELEVANCE = 0.9
PRELOAD_CATEGORIES = ("Vegetables", "Fruits")
# Extra geocode query for markets whose AGMARKNET spelling or new district the geocoder does not know; the hit must
# still confirm a source coordinate. 28-madanapalli: "Madanapalle, Chittoor" (district split in 2022).
QUERY_ALIASES = {"28-madanapalli": "Madanapalle, Chittoor, Andhra Pradesh, India"}
STATES = {  # state name in the source -> code used by config/assumptions.json per-state overrides
    "Andaman and Nicobar": "AN", "Andaman and Nicobar Islands": "AN", "Andhra Pradesh": "AP", "Arunachal Pradesh": "AR", "Assam": "AS", "Bihar": "BR",
    "Chandigarh": "CH", "Chhattisgarh": "CG", "Dadra and Nagar Haveli": "DN", "Daman and Diu": "DD",
    "Dadra and Nagar Haveli and Daman and Diu": "DN", "Goa": "GA", "Gujarat": "GJ", "Haryana": "HR",
    "Himachal Pradesh": "HP", "Jammu and Kashmir": "JK", "Jharkhand": "JH", "Karnataka": "KA", "Kerala": "KL",
    "Ladakh": "LA", "Lakshadweep": "LD", "Madhya Pradesh": "MP", "Maharashtra": "MH", "Manipur": "MN",
    "Meghalaya": "ML", "Mizoram": "MZ", "Nagaland": "NL", "NCT of Delhi": "DL", "Delhi": "DL", "Odisha": "OD",
    "Puducherry": "PY", "Pondicherry": "PY", "Punjab": "PB", "Rajasthan": "RJ", "Sikkim": "SK", "Tamil Nadu": "TN",
    "Telangana": "TG", "Tripura": "TR", "Uttar Pradesh": "UP", "Uttarakhand": "UK", "West Bengal": "WB",
}


def state_code(name):
    key = name.replace("&", "and").strip().lower()
    return {k.lower(): v for k, v in STATES.items()}.get(key)


def in_india(c):
    return c and c[0] is not None and c[1] is not None and 6 <= c[0] <= 37.5 and 68 <= c[1] <= 97.5


def km(a, b):
    p = math.pi / 180
    h = (math.sin((b[0] - a[0]) * p / 2) ** 2
         + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(h))


def resolve(m, geocode):
    """(lat, lon, coord_source, coord_confidence) for one market."""
    srcs = {k: tuple(v) for k, v in m["coords"].items() if in_india(tuple(v))}
    if len(srcs) == 1 or (len(srcs) == 2 and km(srcs["old"], srcs["new"]) <= AGREE_KM):
        kind = "new" if "new" in srcs else "old"
        return (*srcs[kind], f"idp {kind} source", "high")
    queries = [f"{m['name']}, {m['district']}, {m['state_name']}, India", f"{m['name']}, {m['state_name']}, India"]
    queries += [QUERY_ALIASES[m["market_id"]]] if m["market_id"] in QUERY_ALIASES else []
    hits = [h for h in map(geocode, queries) if h and h[2] >= MIN_RELEVANCE]
    for h in hits:
        for kind in ("new", "old"):
            if kind in srcs and km(srcs[kind], h[:2]) <= AGREE_KM:
                return (*srcs[kind], f"idp {kind} source, confirmed by amazon location", "high")
    if not srcs and hits:
        return (hits[0][0], hits[0][1], "amazon location place search (no source coordinates)", "high")
    best = srcs.get("new") or srcs.get("old") or (None, None)
    return (*best, "idp; sources disagree or missing, not confirmed by amazon location", "low")


def main(idp, index, top, dry_run):
    idp = pathlib.Path(idp)
    raw = json.loads((idp / "markets_raw.json").read_text(encoding="utf-8"))
    cache_path = idp / "geocode_cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    loc = None

    def geocode(text):
        nonlocal loc
        if text not in cache:
            if dry_run:
                return None
            if loc is None:
                import boto3
                loc = boto3.client("location", region_name="ap-south-1")
            hits = loc.search_place_index_for_text(IndexName=index, Text=text, FilterCountries=["IND"],
                                                   MaxResults=1)["Results"]
            cache[text] = ([*reversed(hits[0]["Place"]["Geometry"]["Point"]), hits[0].get("Relevance", 0)]
                           if hits else None)
            cache_path.write_text(json.dumps(cache))
        return cache[text]

    markets, unknown_states = [], set()
    for m in raw:
        st = state_code(m["state_name"])
        if st is None:
            unknown_states.add(m["state_name"])
        lat, lon, source, conf = resolve(m, geocode)
        markets.append({"market_id": m["market_id"], "name": re.sub(r"\s+,", ",", m["name"]), "district": m["district"],
                        "state": st or m["state_name"], "lat": None if lat is None else round(lat, 5),
                        "lon": None if lon is None else round(lon, 5), "coord_source": source,
                        "coord_confidence": conf})
    commodities = json.loads((idp / "commodities.json").read_text(encoding="utf-8"))
    fv = [c["crop_id"] for c in sorted(commodities, key=lambda c: -c["markets"]) if c["category"] in PRELOAD_CATEGORIES]
    for c in commodities:
        c["preload"] = c["crop_id"] in fv[:top]
    summary = {"markets": len(markets), "low_confidence": sum(m["coord_confidence"] == "low" for m in markets),
               "geocoded": len(cache), "unknown_states": sorted(unknown_states), "preload": fv[:top]}
    print(json.dumps(summary, indent=1))
    if dry_run:
        return markets
    note = ("AGMARKNET markets from the India Data Portal bulk files (D24), built by scripts/build_idp_config.py. "
            "market_id = census state code + normalised name. Coordinates from the source data; disputed or missing "
            "ones checked with Amazon Location; coord_confidence low = left out of routing.")
    lines = ",\n".join("    " + json.dumps(m, ensure_ascii=False) for m in markets)
    (ROOT / "config/markets.json").write_text('{\n  "_note": ' + json.dumps(note) + ',\n  "markets": [\n'
                                              + lines + "\n  ]\n}\n", encoding="utf-8")
    note = ("Every AGMARKNET commodity in the India Data Portal bulk files (D24). preload: loaded into MarketRisk "
            "daily (top fruits and vegetables by reporting markets); any other is loaded on request "
            "(POST /crops/fetch). Routing needs a full profile in config/crops/.")
    keep = ("crop_id", "name", "category", "markets", "market_days", "from", "to", "preload")
    lines = ",\n".join("    " + json.dumps({k: c.get(k) for k in keep}, ensure_ascii=False) for c in commodities)
    (ROOT / "config/commodities.json").write_text('{\n  "_note": ' + json.dumps(note) + ',\n  "commodities": [\n'
                                                  + lines + "\n  ]\n}\n", encoding="utf-8")
    return markets


def snapshot(idp, markets, crops, origin, radius):
    """Offline demo snapshot: the crops' rows for markets within radius km of origin (usable coordinates only)."""
    near = {m["market_id"] for m in markets if m["lat"] is not None and m["coord_confidence"] != "low"
            and km(origin, (m["lat"], m["lon"])) <= radius}
    for crop in crops:
        with gzip.open(pathlib.Path(idp) / f"{crop}.csv.gz", "rt", newline="", encoding="utf-8") as fh:
            r = csv.DictReader(fh)
            rows = [row for row in r if row["market_id"] in near]
        days = sorted(row["date"] for row in rows)
        out = ROOT / f"data/snapshot/idp_{crop}_{days[0]}_{days[-1]}.csv.gz"
        with open(out, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz, \
                io.TextIOWrapper(gz, encoding="utf-8", newline="") as fh:  # mtime 0: byte-reproducible
            w = csv.DictWriter(fh, r.fieldnames)
            w.writeheader()
            w.writerows(rows)
        print(f"{out.name}: {len(rows)} rows, {len({row['market_id'] for row in rows})} markets")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--idp", required=True)
    ap.add_argument("--index", required=True, help="Amazon Location place index (stack output PlaceIndexName)")
    ap.add_argument("--top", type=int, default=50)  # D28
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--snapshot-crops", help="comma-separated crop ids for data/snapshot/")
    ap.add_argument("--snapshot-origin", default="13.137,78.134", help="lat,lon (default: Kolar demo origin)")
    ap.add_argument("--snapshot-radius", type=float, default=350)
    a = ap.parse_args()
    markets = main(a.idp, a.index, a.top, a.dry_run)
    if a.snapshot_crops and not a.dry_run:
        snapshot(a.idp, markets, a.snapshot_crops.split(","), tuple(map(float, a.snapshot_origin.split(","))),
                 a.snapshot_radius)

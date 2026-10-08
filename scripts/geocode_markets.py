"""Geocode config/markets.json with Amazon Location place search (CLAUDE.md Section 8.3).

Query: "<market>, <district>, <state>, India". Writes lat, lon, coord_source and coord_confidence
("high" when Relevance >= 0.9, else "low"; low-confidence markets are skipped by routing until fixed).
Markets with "coord_override": true keep their coordinates. Needs the team's AWS credentials.

Usage: python scripts/geocode_markets.py --index <place-index-name> [--dry-run]
"""
import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MARKETS = ROOT / "config" / "markets.json"
STATES = {"KA": "Karnataka", "AP": "Andhra Pradesh", "TN": "Tamil Nadu", "MH": "Maharashtra", "TG": "Telangana",
          "KL": "Kerala"}
MIN_RELEVANCE = 0.9


def main(index, dry_run):
    import boto3
    loc = boto3.client("location", region_name="ap-south-1")
    doc = json.loads(MARKETS.read_text(encoding="utf-8"))
    for m in doc["markets"]:
        if m.get("coord_override"):
            continue
        text = f"{m['name']}, {m['district']}, {STATES.get(m['state'], m['state'])}, India"
        res = loc.search_place_index_for_text(IndexName=index, Text=text, FilterCountries=["IND"], MaxResults=1)
        hits = res["Results"]
        if not hits:
            m["coord_confidence"] = "low"
            print(f"{m['market_id']}: no result for {text!r}")
            continue
        lon, lat = hits[0]["Place"]["Geometry"]["Point"]
        rel = hits[0].get("Relevance", 0)
        m.update(lat=round(lat, 4), lon=round(lon, 4), coord_source=f"amazon location {index}: {text}",
                 coord_confidence="high" if rel >= MIN_RELEVANCE else "low")
        print(f"{m['market_id']}: {lat:.4f},{lon:.4f} relevance {rel:.2f} ({hits[0]['Place'].get('Label')})")
    if not dry_run:
        MARKETS.write_text(_dump(doc), encoding="utf-8")


def _dump(doc):
    """Same layout as the committed file: one market per line."""
    lines = ",\n".join("    " + json.dumps(m, ensure_ascii=False) for m in doc["markets"])
    rest = "".join(f',\n  "{k}": ' + json.dumps(v, ensure_ascii=False, indent=2).replace("\n", "\n  ")
                   for k, v in doc.items() if k not in ("_note", "markets"))
    return ('{\n  "_note": ' + json.dumps(doc["_note"], ensure_ascii=False) + ',\n  "markets": [\n'
            + lines + "\n  ]" + rest + "\n}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True, help="Amazon Location place index (stack output PlaceIndexName)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    main(a.index, a.dry_run)

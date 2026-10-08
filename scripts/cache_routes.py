"""Fill data/routes_cache.json with Amazon Location routes for origins x every market and outlet (D11).

Run with AWS credentials and LOCATION_ROUTE_CALCULATOR set (region ap-south-1):
  python scripts/cache_routes.py 13.137,78.134 <village_id>=<lat>,<lon> [--refresh]
An origin "lat,lon" is keyed by lat,lon rounded to 3 dp; "<village_id>=lat,lon" is keyed by village_id,
which the API matches exactly against origin.place. Existing entries are kept unless --refresh.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.adapters import location  # noqa: E402


def parse_origin(arg):
    name, _, coords = arg.rpartition("=")
    lat, lon = (float(x) for x in coords.split(","))
    return (name or location.origin_key(lat, lon)), {"lat": lat, "lon": lon}


def main(argv):
    refresh = "--refresh" in argv
    origins = [parse_origin(a) for a in argv if a != "--refresh"]
    if not origins:
        sys.exit(__doc__)
    markets = json.loads((ROOT / "config/markets.json").read_text())["markets"]
    outlets = json.loads((ROOT / "config/outlets.json").read_text())["outlets"]
    dests = [(m["market_id"], m) for m in markets] + [(o["outlet_id"], o) for o in outlets]
    path = pathlib.Path(location.cache_path())
    cache = json.loads(path.read_text())
    for key, origin in origins:
        for dest_id, dest in dests:
            k = f"{key}|{dest_id}"
            if k in cache and not refresh:
                continue
            cache[k] = location.calculate_route(origin, dest)
            print(k, cache[k]["distance_km"], "km", round(cache[k]["drive_hours"], 2), "h")
            path.write_text(json.dumps(cache, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])

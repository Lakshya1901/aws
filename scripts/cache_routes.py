"""Fill data/routes_cache.json with Amazon Location routes for origins x every market and outlet within
max_radius_km straight-line (D11; the advisor never routes beyond it).

Run with AWS credentials and LOCATION_ROUTE_CALCULATOR set (region ap-south-1):
  python scripts/cache_routes.py 13.137,78.134 <village_id>=<lat>,<lon> [--refresh] [--rescue]
An origin "lat,lon" is keyed by lat,lon rounded to 3 dp; "<village_id>=lat,lon" is keyed by village_id,
which the API matches exactly against origin.place. Existing entries are kept unless --refresh. --rescue routes only
to outlets within rescue_radius_km (Rescue, D31).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.adapters import location  # noqa: E402
from backend.core.config import assumption  # noqa: E402
from backend.core.netvalue import haversine_km  # noqa: E402


def parse_origin(arg):
    name, _, coords = arg.rpartition("=")
    lat, lon = (float(x) for x in coords.split(","))
    return (name or location.origin_key(lat, lon)), {"lat": lat, "lon": lon}


def main(argv):
    refresh, rescue = "--refresh" in argv, "--rescue" in argv
    origins = [parse_origin(a) for a in argv if a not in ("--refresh", "--rescue")]
    if not origins:
        sys.exit(__doc__)
    markets = json.loads((ROOT / "config/markets.json").read_text())["markets"]
    outlets = json.loads((ROOT / "config/outlets.json").read_text())["outlets"]
    dests = [] if rescue else [(m["market_id"], m) for m in markets
                               if m.get("lat") is not None and m.get("coord_confidence") != "low"]
    dests += [(o["outlet_id"], o) for o in outlets]
    radius = assumption(json.loads((ROOT / "config/assumptions.json").read_text()),
                        "rescue_radius_km" if rescue else "max_radius_km")
    path = pathlib.Path(location.cache_path())
    cache = json.loads(path.read_text())
    for key, origin in origins:
        for dest_id, dest in dests:
            if haversine_km(origin["lat"], origin["lon"], dest["lat"], dest["lon"]) > radius:
                continue
            k = f"{key}|{dest_id}"
            if k in cache and not refresh:
                continue
            try:
                cache[k] = location.calculate_route(origin, dest)
            except Exception as e:  # e.g. coordinates off the road network: left out, the API falls back to approx
                print(k, "skipped:", str(e)[:120])
                continue
            print(k, cache[k]["distance_km"], "km", round(cache[k]["drive_hours"], 2), "h")
            path.write_text(json.dumps(cache, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])

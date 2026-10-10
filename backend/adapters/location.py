"""Road distance and drive time from Amazon Location Service, cached in data/routes_cache.json (D11), and typed
places geocoded with Amazon Location place search, cached in data/places_cache.json (D31).

Cache key "<origin_key>|<outlet_id>": origin_key is "lat,lon" rounded to 3 dp, or a named demo village id
(matched exactly against origin["place"]). Live calls happen only when DATA_SOURCE=dynamodb and
LOCATION_ROUTE_CALCULATOR is set, or from scripts/cache_routes.py; never in tests or snapshot mode.
"""
import json
import os
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
REGION = "ap-south-1"
_live = {}  # routes fetched live in this process (the Lambda package is read-only)


def cache_path():
    return os.environ.get("ROUTES_CACHE") or os.path.join(ROOT, "data", "routes_cache.json")


def origin_key(lat, lon):
    return f"{lat:.3f},{lon:.3f}"


def calculate_route(origin, dest, calculator=None):
    """{distance_km, drive_hours, source, fetched_at} from Amazon Location CalculateRoute (truck mode)."""
    import boto3  # lazy: tests and snapshot mode never need it
    calculator = calculator or os.environ["LOCATION_ROUTE_CALCULATOR"]
    resp = boto3.client("location", region_name=REGION).calculate_route(
        CalculatorName=calculator, DeparturePosition=[origin["lon"], origin["lat"]],
        DestinationPosition=[dest["lon"], dest["lat"]], TravelMode="Truck", DistanceUnit="Kilometers")
    s = resp["Summary"]
    return {"distance_km": s["Distance"], "drive_hours": s["DurationSeconds"] / 3600,
            "source": f"amazon_location:{calculator}", "fetched_at": datetime.now(timezone.utc).isoformat()}


def routes_for(origin, destinations, live=True):
    """{dest_id: {distance_km, drive_hours}} for destinations [{id, lat, lon}] with a cached or live route.

    Destinations without a route are left out; the core then raises drive_time_unavailable.
    """
    with open(cache_path(), encoding="utf-8") as fh:
        known = {**json.load(fh), **_live}
    keys = [origin_key(origin["lat"], origin["lon"])] + ([origin["place"]] if origin.get("place") else [])
    live = live and os.environ.get("DATA_SOURCE") == "dynamodb" and os.environ.get("LOCATION_ROUTE_CALCULATOR")
    out = {}
    for d in destinations:
        hit = next((known[f"{k}|{d['id']}"] for k in keys if f"{k}|{d['id']}" in known), None)
        if hit is None and live:
            hit = _live[f"{keys[0]}|{d['id']}"] = calculate_route(origin, d)
        if hit is not None:
            out[d["id"]] = {"distance_km": hit["distance_km"], "drive_hours": hit["drive_hours"]}
    return out


MIN_PLACE_RELEVANCE = 0.9  # below this the match is too loose to route from (assumption)
_live_places = {}


def places_path():
    return os.environ.get("PLACES_CACHE") or os.path.join(ROOT, "data", "places_cache.json")


def search_place(text, index):
    """{lat, lon, label, relevance, source, fetched_at} for the best match in India, or None below
    MIN_PLACE_RELEVANCE."""
    import boto3  # lazy: tests and snapshot mode never need it
    res = boto3.client("location", region_name=REGION).search_place_index_for_text(
        IndexName=index, Text=text, FilterCountries=["IND"], MaxResults=1)["Results"]
    if not res or res[0].get("Relevance", 0) < MIN_PLACE_RELEVANCE:
        return None
    lon, lat = res[0]["Place"]["Geometry"]["Point"]
    return {"lat": round(lat, 5), "lon": round(lon, 5), "label": res[0]["Place"].get("Label"),
            "relevance": res[0]["Relevance"], "source": f"amazon_location:{index}",
            "fetched_at": datetime.now(timezone.utc).isoformat()}


def geocode_place(key, text):
    """A typed city, town or village (key = its normalised form) from the cache, else live when DATA_SOURCE=dynamodb
    and LOCATION_PLACE_INDEX are set. None when not found."""
    try:
        with open(places_path(), encoding="utf-8") as fh:
            known = {**json.load(fh), **_live_places}
    except FileNotFoundError:
        known = dict(_live_places)
    if key in known:
        return known[key]
    index = os.environ.get("LOCATION_PLACE_INDEX")
    if os.environ.get("DATA_SOURCE") == "dynamodb" and index:
        _live_places[key] = search_place(text, index)
        return _live_places[key]
    return None


if __name__ == "__main__":
    # python backend/adapters/location.py <place-index> <place>...: add places to data/places_cache.json
    import sys
    sys.path.insert(0, os.path.join(ROOT))
    from backend.handlers.advisor import _place_key
    path = places_path()
    cache = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    for name in sys.argv[2:]:
        cache[_place_key(name)] = hit = search_place(name, sys.argv[1])
        print(name, hit)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(cache, indent=1, ensure_ascii=False) + "\n")

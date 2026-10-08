"""Road distance and drive time from Amazon Location Service, cached in data/routes_cache.json (D11).

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


def routes_for(origin, destinations):
    """{dest_id: {distance_km, drive_hours}} for destinations [{id, lat, lon}] with a cached or live route.

    Destinations without a route are left out; the core then raises drive_time_unavailable.
    """
    with open(cache_path(), encoding="utf-8") as fh:
        known = {**json.load(fh), **_live}
    keys = [origin_key(origin["lat"], origin["lon"])] + ([origin["place"]] if origin.get("place") else [])
    live = os.environ.get("DATA_SOURCE") == "dynamodb" and os.environ.get("LOCATION_ROUTE_CALCULATOR")
    out = {}
    for d in destinations:
        hit = next((known[f"{k}|{d['id']}"] for k in keys if f"{k}|{d['id']}" in known), None)
        if hit is None and live:
            hit = _live[f"{keys[0]}|{d['id']}"] = calculate_route(origin, d)
        if hit is not None:
            out[d["id"]] = {"distance_km": hit["distance_km"], "drive_hours": hit["drive_hours"]}
    return out

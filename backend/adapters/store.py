"""Data access for the advisor (CLAUDE.md Section 8.5). DATA_SOURCE=snapshot (default) | dynamodb.

snapshot: market days from data/snapshot/*_<crop>_*.csv, outlets from config/outlets.json, plans in an
in-process dict (plus PLANS_FILE, a local JSON file, when set).
dynamodb: tables named by env MARKET_RISK_TABLE, OUTLETS_TABLE, PLANS_TABLE. Market risk comes precomputed from
MarketRisk (written by ingest, D24); a "#status" row per crop records whether its data is loaded. Fetch requests
go to the SQS queue in FETCH_QUEUE_URL. Markets, crops and assumptions always come from config/.
Temperature comes from weather snapshot files data/snapshot/weather_*.json (backend/adapters/weather.py: Open-Meteo or NASA POWER).
"""
import csv
import glob
import gzip
import json
import os
from decimal import Decimal
from functools import lru_cache
from backend.core.config import assumption, load_configs
from backend.core.netvalue import haversine_km
from backend.core.recommend import market_context

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
_plans = {}


def _source():
    return os.environ.get("DATA_SOURCE", "snapshot")


def config_dir():
    return os.environ.get("CONFIG_DIR") or os.path.join(ROOT, "config")


def snapshot_dir():
    return os.environ.get("SNAPSHOT_DIR") or os.path.join(ROOT, "data", "snapshot")


@lru_cache(maxsize=4)
def _configs(path):
    return load_configs(path)


def configs():
    return _configs(config_dir())


def _table(env):
    import boto3  # lazy: tests and snapshot mode never need it
    return boto3.resource("dynamodb", region_name="ap-south-1").Table(os.environ[env])


def _plain(x):
    """DynamoDB Decimals back to int/float."""
    if isinstance(x, Decimal):
        return int(x) if x == x.to_integral_value() else float(x)
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_plain(v) for v in x]
    return x


def _num(v):
    return float(v) if v not in ("", None) else None


def _snapshot_files(path, crop):
    """Snapshot CSVs (plain or gzipped) whose name carries the crop; rows are still filtered by their crop column
    because crop ids share prefixes (onion, onion_green)."""
    return sorted(glob.glob(os.path.join(path, f"*_{crop}_*.csv")) + glob.glob(os.path.join(path, f"*_{crop}_*.csv.gz")))


@lru_cache(maxsize=8)
def _snapshot_rows(path, crop):
    rows = []
    for f in _snapshot_files(path, crop):
        with (gzip.open(f, "rt", newline="", encoding="utf-8") if f.endswith(".gz")
              else open(f, newline="", encoding="utf-8")) as fh:
            rows += [{"date": r["date"], "market_id": r["market_id"], "crop": crop,
                      "arrivals_t": _num(r["arrivals_t"]), "modal_price_kg": _num(r["modal_price_kg"])}
                     for r in csv.DictReader(fh) if r["crop"] == crop]
    return rows


def market_days(crop, as_of_date):
    """Rows {date, market_id, crop, arrivals_t, modal_price_kg} on or before as_of_date."""
    if _source() != "dynamodb":
        return [r for r in _snapshot_rows(snapshot_dir(), crop) if r["date"] <= as_of_date]
    from boto3.dynamodb.conditions import Key
    table, rows = _table("MARKET_DAY_TABLE"), []
    for m in configs()["markets"]:
        kw = {"KeyConditionExpression": Key("market_crop").eq(f"{m['market_id']}#{crop}") & Key("date").lte(as_of_date)}
        while True:
            page = table.query(**kw)
            rows += [{"date": i["date"], "market_id": m["market_id"], "crop": crop,
                      "arrivals_t": _plain(i.get("arrivals_t")), "modal_price_kg": _plain(i.get("modal_price_kg"))}
                     for i in page["Items"]]
            if "LastEvaluatedKey" not in page:
                break
            kw["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    return rows


RISK_FIELDS = ("market_id", "as_of_date", "latest_date", "stale", "data_complete", "days_of_last_7", "a7_t",
               "a7_sum_t", "baseline_t", "arrival_ratio", "price_kg", "arrivals_t", "price_change_3d", "risk_level")
STATUS_KEY = "#status"


def risk_item(crop, as_of_date, mode, c):
    """MarketRisk item for one market_context entry (written by ingest, read back by contexts())."""
    m, risk, fit = c["market"], c["risk"], c["fit"]
    return {**{k: risk[k] for k in RISK_FIELDS}, "crop": crop, "as_of_date": as_of_date, "mode": mode,
            "lead_days": None, "elasticity_b": fit["b"], "resid_sd": fit["resid_sd"],
            "state": m["state"], "lat": m["lat"], "lon": m["lon"], "name": m.get("name")}


def contexts(crop, as_of_date):
    """market_context entries [{market, risk, fit}] for a crop.

    snapshot: computed from the snapshot rows. dynamodb: read from MarketRisk, which ingest fills for the same
    as_of_date (replay date or today); markets come from config/markets.json.
    """
    cfg = configs()
    if _source() != "dynamodb":
        return market_context(crop, market_days(crop, as_of_date), cfg["markets"], cfg, as_of_date)
    from boto3.dynamodb.conditions import Key
    table, items, kw = _table("MARKET_RISK_TABLE"), [], {"KeyConditionExpression": Key("crop").eq(crop)}
    while True:
        page = table.query(**kw)
        items += page["Items"]
        if "LastEvaluatedKey" not in page:
            break
        kw["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    by_id = {m["market_id"]: m for m in cfg["markets"]}
    out = []
    for i in _plain(items):
        m = by_id.get(i["market_id"])
        if i["market_id"] == STATUS_KEY or i.get("as_of_date") != as_of_date or m is None or m.get("lat") is None or m.get("coord_confidence") == "low":
            continue
        out.append({"market": m, "risk": {k: i.get(k) for k in RISK_FIELDS},
                    "fit": {"b": i["elasticity_b"], "resid_sd": i["resid_sd"]}})
    return out


def crop_status(crop, as_of_date):
    """"ready" when the crop's risk is loaded for as_of_date, "fetching" while a fetch is queued, else "available"."""
    if _source() != "dynamodb":
        return "ready" if _snapshot_files(snapshot_dir(), crop) else "available"
    item = _table("MARKET_RISK_TABLE").get_item(Key={"crop": crop, "market_id": STATUS_KEY}).get("Item")
    if not item or (item["status"] == "ready" and item.get("as_of_date") != as_of_date):
        return "available"
    return item["status"]


def request_fetch(crop, as_of_date):
    """Queue a fetch of one crop's data (SQS -> ingest, D24). Returns the new status."""
    import boto3
    from datetime import datetime, timezone
    _table("MARKET_RISK_TABLE").put_item(Item={"crop": crop, "market_id": STATUS_KEY, "status": "fetching",
                                              "requested_at": datetime.now(timezone.utc).isoformat()})
    boto3.client("sqs", region_name="ap-south-1").send_message(
        QueueUrl=os.environ["FETCH_QUEUE_URL"], MessageBody=json.dumps({"crop": crop, "as_of_date": as_of_date}))
    return "fetching"


def outlets():
    if _source() != "dynamodb":
        return configs()["outlets"]
    table, items, kw = _table("OUTLETS_TABLE"), [], {}
    while True:
        page = table.scan(**kw)
        items += page["Items"]
        if "LastEvaluatedKey" not in page:
            return _plain(items)
        kw["ExclusiveStartKey"] = page["LastEvaluatedKey"]


@lru_cache(maxsize=4)
def _weather_files(path):
    out = []
    for f in sorted(glob.glob(os.path.join(path, "weather_*.json"))):
        with open(f, encoding="utf-8") as fh:
            out.append(json.load(fh))
    return out


def temperature_c(lat, lon, day):
    """Mean of the temperatures on `day` at the weather point nearest to (lat, lon), or None.

    Points are the markets (or NOAA stations) in a weather snapshot file whose from..to covers the day, within
    max_radius_km. With no snapshot point and WEATHER_LIVE=1: weather.live_temperature_c.
    """
    best, radius = None, assumption(configs()["assumptions"], "max_radius_km")
    for w in _weather_files(snapshot_dir()):
        if not w["from"] <= day <= w["to"]:
            continue
        for p in w["markets"].values():
            temps = [t for ts, t in zip(p["time"], p["temperature_c"]) if ts.startswith(day) and t is not None]
            d = haversine_km(lat, lon, p["lat"], p["lon"])
            if temps and d <= radius and (best is None or d < best[0]):
                best = (d, sum(temps) / len(temps))
    if best is None and os.environ.get("WEATHER_LIVE") == "1":  # deployed: live forecast or NOAA GHCN (D29)
        from datetime import datetime, timedelta, timezone
        from backend.adapters import weather
        today = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).date().isoformat()
        try:
            return weather.live_temperature_c(lat, lon, day, today)
        except Exception:  # network or data failure: the caller's 422 / split_required path, as without weather
            return None
    return None if best is None else best[1]


def _plans_file():
    """PLANS_FILE path (snapshot mode), merging its saved plans into memory first."""
    path = os.environ.get("PLANS_FILE")
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            _plans.update({k: v for k, v in json.load(fh).items() if k not in _plans})
    return path


def get_plan(plan_id):
    if _source() == "dynamodb":
        item = _table("PLANS_TABLE").get_item(Key={"plan_id": plan_id}).get("Item")
        return _plain(item) if item else None
    _plans_file()
    return _plans.get(plan_id)


def put_plan(plan):
    if _source() == "dynamodb":
        _table("PLANS_TABLE").put_item(Item=json.loads(json.dumps(plan), parse_float=Decimal))
        return
    path = _plans_file()
    _plans[plan["plan_id"]] = plan
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(_plans, fh, ensure_ascii=False)

"""Daily ingest (CLAUDE.md Sections 8.5, 15.1): CEDA/AGMARKNET -> S3 raw, MarketDay, MarketRisk.

Run by EventBridge Scheduler at 21:00 IST. Any market that fails is logged; the run then raises so the
CloudWatch alarm on Lambda errors fires. Markets that succeeded are still written.
"""
import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from backend.adapters import ceda
from backend.core.config import crop_mode, load_configs
from backend.core.recommend import market_context

log = logging.getLogger()
log.setLevel(logging.INFO)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")
IST = timezone(timedelta(hours=5, minutes=30))
FETCH_DAYS = 14          # re-pull the last two weeks each day (CEDA back-fills)
HISTORY_DAYS = 4 * 366   # prior years for the seasonal baseline B


def _ddb():
    import boto3
    return boto3.resource("dynamodb")


def _s3():
    import boto3
    return boto3.client("s3")


def _dec(obj):
    """Floats -> Decimal for DynamoDB."""
    return json.loads(json.dumps(obj, default=str), parse_float=Decimal)


def _undec(obj):
    return json.loads(json.dumps(obj, default=lambda d: float(d) if d % 1 else int(d)))


def _history(table, market_id, crop, start, end):
    from boto3.dynamodb.conditions import Key
    cond = Key("market_crop").eq(f"{market_id}#{crop}") & Key("date").between(start, end)
    rows, kwargs = [], {"KeyConditionExpression": cond}
    while True:
        page = table.query(**kwargs)
        rows += page["Items"]
        if "LastEvaluatedKey" not in page:
            return [dict(_undec(r), market_id=market_id, crop=crop) for r in rows]
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def handler(event, context):
    configs = load_configs(CONFIG_DIR)
    as_of = (event or {}).get("as_of_date") or configs["model"].get("replay_date") \
        or datetime.now(IST).date().isoformat()
    start = (date.fromisoformat(as_of) - timedelta(days=FETCH_DAYS)).isoformat()
    ddb, s3, bucket = _ddb(), _s3(), os.environ["DATA_BUCKET"]
    day_table = ddb.Table(os.environ["MARKET_DAY_TABLE"])
    risk_table = ddb.Table(os.environ["MARKET_RISK_TABLE"])
    markets = [m for m in configs["markets"] if m.get("ceda")]
    failed, summary = [], {}
    for crop in [c for c in configs["crops"] if c in ceda.COMMODITY_IDS]:
        raw_all, written = {}, 0
        for m in markets:
            try:
                raw = ceda.fetch_raw(crop, m["ceda"]["state_id"], m["ceda"]["district_id"], start, as_of)
                raw_all[m["market_id"]] = raw
                ingested_at = datetime.now(timezone.utc).isoformat()
                with day_table.batch_writer(overwrite_by_pkeys=["market_crop", "date"]) as bw:
                    for r in ceda.normalise(raw, m["market_id"], crop):
                        item = {k: v for k, v in r.items() if k not in ("market_id", "crop")}
                        bw.put_item(Item=_dec({**item, "market_crop": f"{m['market_id']}#{crop}",
                                               "ingested_at": ingested_at}))
                        written += 1
            except Exception:
                log.exception("ingest failed for %s/%s", crop, m["market_id"])
                failed.append(f"{crop}/{m['market_id']}")
        s3.put_object(Bucket=bucket, Key=f"raw/agmarknet/{crop}/{as_of}.json", ContentType="application/json",
                      Body=json.dumps({"source": ceda.BASE, "as_of_date": as_of, "markets": raw_all}).encode())

        hist_start = (date.fromisoformat(as_of) - timedelta(days=HISTORY_DAYS)).isoformat()
        rows = [r for m in markets for r in _history(day_table, m["market_id"], crop, hist_start, as_of)]
        ctx = market_context(crop, rows, configs["markets"], configs, as_of)
        mode = crop_mode(configs["model"], crop)
        with risk_table.batch_writer(overwrite_by_pkeys=["crop", "market_id"]) as bw:
            for c in ctx:
                m, risk = c["market"], c["risk"]
                bw.put_item(Item=_dec({**risk, "crop": crop, "as_of_date": as_of, "mode": mode,
                                       "lead_days": None, "elasticity_b": c["fit"]["b"],
                                       "state": m["state"], "lat": m["lat"], "lon": m["lon"]}))
        summary[crop] = {"market_day_rows": written, "market_risk_rows": len(ctx)}
    log.info(json.dumps({"ingest": summary, "as_of_date": as_of, "failed": failed}))
    if failed:
        raise RuntimeError(f"ingest failed for {', '.join(failed)}")
    return summary

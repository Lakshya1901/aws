"""Ingest (CLAUDE.md Sections 8.5, 15.1, D24): per-commodity market-level history in S3 -> MarketRisk.

Triggers: EventBridge Scheduler at 21:00 IST queues every preload crop in config/commodities.json on the SQS fetch
queue (one invocation per crop keeps each run far inside the Lambda limit); the queue also carries crops users ask
for (POST /crops/fetch). A direct invoke with {"crops": [...], "as_of_date": ...} processes those crops inline.
Each crop: reads s3://<DATA_BUCKET>/idp/<crop>.csv.gz (scripts/build_idp.py: rows sorted by market, then date), computes each market's risk and price fit for the
as-of date one market at a time, and writes MarketRisk plus the crop's "#status" row (ready). Any crop that
fails is logged and the run raises, so the CloudWatch alarm fires and SQS retries, then dead-letters.
"""
import csv
import gzip
import io
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import groupby

from backend.adapters.store import STATUS_KEY, risk_item
from backend.core.config import crop_mode, load_configs
from backend.core.recommend import market_context

log = logging.getLogger()
log.setLevel(logging.INFO)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")
IST = timezone(timedelta(hours=5, minutes=30))


def _ddb():
    import boto3
    return boto3.resource("dynamodb")


def _s3():
    import boto3
    return boto3.client("s3")


def _dec(obj):
    """Floats -> Decimal for DynamoDB."""
    return json.loads(json.dumps(obj, default=str), parse_float=Decimal)


def _num(v):
    return float(v) if v not in ("", None) else None


def crop_contexts(lines, crop, configs, as_of):
    """market_context entries for one crop from its CSV lines (sorted by market_id), one market at a time."""
    markets = {m["market_id"]: m for m in configs["markets"]}
    out = []
    for market_id, rows in groupby(csv.DictReader(lines), key=lambda r: r["market_id"]):
        m = markets.get(market_id)
        if m is None:
            continue
        rows = [{"date": r["date"], "market_id": market_id, "crop": crop, "arrivals_t": _num(r["arrivals_t"]),
                 "modal_price_kg": _num(r["modal_price_kg"])} for r in rows if r["date"] <= as_of]
        out += market_context(crop, rows, [m], configs, as_of)
    return out


def ingest_crop(crop, as_of, configs, s3, table, bucket):
    body = s3.get_object(Bucket=bucket, Key=f"idp/{crop}.csv.gz")["Body"]
    with io.TextIOWrapper(gzip.GzipFile(fileobj=body), encoding="utf-8", newline="") as lines:
        ctx = crop_contexts(lines, crop, configs, as_of)
    mode = crop_mode(configs["model"], crop)
    with table.batch_writer(overwrite_by_pkeys=["crop", "market_id"]) as bw:
        for c in ctx:
            bw.put_item(Item=_dec(risk_item(crop, as_of, mode, c)))
        bw.put_item(Item=_dec({"crop": crop, "market_id": STATUS_KEY, "status": "ready", "as_of_date": as_of,
                               "markets": len(ctx), "ingested_at": datetime.now(timezone.utc).isoformat()}))
    return len(ctx)


def handler(event, context):
    configs = load_configs(CONFIG_DIR)
    event = event or {}
    default_as_of = configs["model"].get("replay_date") or datetime.now(IST).date().isoformat()
    if "Records" in event:  # SQS fetch queue, batch size 1
        jobs = [json.loads(r["body"]) for r in event["Records"]]
    elif event.get("crops"):
        jobs = [{"crop": c, "as_of_date": event.get("as_of_date")} for c in event["crops"]]
    else:  # daily schedule: fan out the preload crops over the queue
        import boto3
        sqs = boto3.client("sqs")
        crops = [c for c, v in configs["commodities"].items() if v.get("preload")]
        for c in crops:
            sqs.send_message(QueueUrl=os.environ["FETCH_QUEUE_URL"],
                             MessageBody=json.dumps({"crop": c, "as_of_date": event.get("as_of_date") or default_as_of}))
        log.info(json.dumps({"queued": crops}))
        return {"queued": crops}
    s3, bucket = _s3(), os.environ["DATA_BUCKET"]
    table = _ddb().Table(os.environ["MARKET_RISK_TABLE"])
    summary, failed = {}, []
    for job in jobs:
        crop, as_of = job["crop"], job.get("as_of_date") or default_as_of
        try:
            summary[crop] = ingest_crop(crop, as_of, configs, s3, table, bucket)
        except Exception:
            log.exception("ingest failed for %s", crop)
            failed.append(crop)
    log.info(json.dumps({"ingest": summary, "failed": failed}))
    if failed:
        raise RuntimeError(f"ingest failed for {', '.join(failed)}")
    return summary

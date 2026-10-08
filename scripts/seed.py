"""Seed AWS from the repo (CLAUDE.md Section 15.4 step 5). Needs the team's AWS credentials.

- Outlets table <- config/outlets.json
- MarketDay table <- data/snapshot/*.csv (PK market_crop = "<market_id>#<crop>", SK date)
- S3 data bucket snapshot/ <- the snapshot CSVs and manifests
Markets stay in config/markets.json (Section 8.5: config lives in versioned JSON, not the database).

Usage: python scripts/seed.py --stack annasetu   (reads table and bucket names from the stack outputs)
"""
import argparse
import csv
import json
import pathlib
from datetime import datetime, timezone
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGION = "ap-south-1"


def _num(v):
    return None if v in ("", None) else Decimal(v)


def main(stack):
    import boto3
    outputs = {o["OutputKey"]: o["OutputValue"] for o in boto3.client("cloudformation", region_name=REGION)
               .describe_stacks(StackName=stack)["Stacks"][0].get("Outputs", [])}
    ddb, s3 = boto3.resource("dynamodb", region_name=REGION), boto3.client("s3", region_name=REGION)

    outlets = json.loads((ROOT / "config/outlets.json").read_text(encoding="utf-8"))["outlets"]
    with ddb.Table(outputs["OutletsTable"]).batch_writer(overwrite_by_pkeys=["outlet_id"]) as bw:
        for o in outlets:
            bw.put_item(Item=json.loads(json.dumps(o), parse_float=Decimal))
    print(f"Outlets: {len(outlets)}")

    ingested_at = datetime.now(timezone.utc).isoformat()
    for path in sorted((ROOT / "data/snapshot").glob("*.csv")):
        n = 0
        with open(path, newline="", encoding="utf-8") as fh, \
                ddb.Table(outputs["MarketDayTable"]).batch_writer(overwrite_by_pkeys=["market_crop", "date"]) as bw:
            for r in csv.DictReader(fh):
                bw.put_item(Item={"market_crop": f"{r['market_id']}#{r['crop']}", "date": r["date"],
                                  "arrivals_t": _num(r["arrivals_t"]), "min_price_kg": _num(r["min_price_kg"]),
                                  "max_price_kg": _num(r["max_price_kg"]), "modal_price_kg": _num(r["modal_price_kg"]),
                                  "source": r["source"], "ingested_at": ingested_at})
                n += 1
        print(f"MarketDay <- {path.name}: {n} rows")
        for f in (path, path.with_suffix(".manifest.json")):
            if f.exists():
                s3.upload_file(str(f), outputs["DataBucket"], f"snapshot/{f.name}")
                print(f"s3://{outputs['DataBucket']}/snapshot/{f.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", default="annasetu")
    main(ap.parse_args().stack)

"""Ingest (D24): per-crop CSV -> market_context, one market at a time, same result as computing it all at once."""
import csv
import io
import json

from backend.adapters import store
from backend.core.config import load_configs
from backend.core.recommend import market_context
from backend.handlers import ingest
from backend.tests.fixtures import AS_OF, CONFIG_DIR, MARKETS, glut_day


def test_crop_contexts_matches_market_context():
    cfg = dict(load_configs(CONFIG_DIR), markets=MARKETS)
    rows = sorted((dict(r, crop="tomato") for r in glut_day()), key=lambda r: (r["market_id"], r["date"]))
    buf = io.StringIO()
    w = csv.DictWriter(buf, ["date", "market_id", "crop", "arrivals_t", "modal_price_kg"])
    w.writeheader()
    w.writerows(rows)
    buf.seek(0)
    got = ingest.crop_contexts(buf, "tomato", cfg, AS_OF)
    want = market_context("tomato", rows, MARKETS, cfg, AS_OF)
    key = lambda c: c["market"]["market_id"]  # noqa: E731
    assert sorted(got, key=key) == sorted(want, key=key) and want
    item = store.risk_item("tomato", AS_OF, "same_day", want[0])
    assert json.loads(json.dumps(item))["resid_sd"] == want[0]["fit"]["resid_sd"]

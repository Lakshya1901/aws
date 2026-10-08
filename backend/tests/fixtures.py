"""Synthetic, deterministic fixtures. Nothing here reads the data snapshot."""
import os
from datetime import date, timedelta
from math import sin

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")
AS_OF = "2025-04-04"
ORIGIN = {"lat": 13.10, "lon": 78.10, "place": "test village near Kolar"}

# Synthetic markets (coordinates of the real towns; data below is invented for tests only).
MARKETS = [
    {"market_id": "kolar", "name": "Kolar", "state": "KA", "lat": 13.1367, "lon": 78.1337},
    {"market_id": "chintamani", "name": "Chintamani", "state": "KA", "lat": 13.3987, "lon": 78.0533},
    {"market_id": "bengaluru", "name": "Bengaluru", "state": "KA", "lat": 12.9768, "lon": 77.5901},
    {"market_id": "madanapalle", "name": "Madanapalle", "state": "AP", "lat": 13.5558, "lon": 78.5015},
]

OUTLETS = [
    {"outlet_id": "proc", "type": "processor", "name": "Test processor", "state": "KA", "lat": 13.34, "lon": 78.21,
     "crops": ["tomato"], "offer_price_kg": None},
    {"outlet_id": "fb", "type": "food_bank", "name": "Test food bank", "state": "KA", "lat": 13.14, "lon": 78.13,
     "crops": ["tomato"], "offer_price_kg": None},
]


def history(market_id, base_t, price_kg, as_of=AS_OF, start="2023-01-01", b=-0.5, noise=0.03,
            last7_mult=1.0, end=None, skip=()):
    """Daily rows: arrivals vary +/-20% around base_t, price follows arrivals with elasticity b.

    last7_mult scales arrivals on the 7 days ending at `end` (default as_of); rows after `end` are omitted;
    dates in `skip` are omitted (missing, never zero).
    """
    d, stop = date.fromisoformat(start), date.fromisoformat(end or as_of)
    rows, i = [], 0
    while d <= stop:
        mult = last7_mult if (stop - d).days < 7 else 1.0
        arr = base_t * (1 + 0.2 * sin(i * 0.7)) * mult
        price = price_kg * (arr / base_t) ** b * (1 + noise * sin(i * 1.3))
        if d.isoformat() not in skip:
            rows.append({"date": d.isoformat(), "market_id": market_id, "arrivals_t": arr, "modal_price_kg": price})
        d += timedelta(days=1)
        i += 1
    return rows


def normal_week():
    return (history("kolar", 100, 20) + history("chintamani", 50, 20) + history("bengaluru", 300, 20)
            + history("madanapalle", 80, 20))


def glut_day():
    return (history("kolar", 100, 20, last7_mult=2.5) + history("chintamani", 50, 20)
            + history("bengaluru", 300, 20) + history("madanapalle", 80, 20))


def load(q=2000, **kw):
    return dict({"crop": "tomato", "quantity_kg": q, "origin": dict(ORIGIN), "harvest": "today", "temp_c": 30}, **kw)

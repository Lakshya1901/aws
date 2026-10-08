"""AGMARKNET daily prices and arrivals via CEDA (Ashoka University), district level.

CEDA serves AGMARKNET data aggregated per Census 2011 district. Units, from CEDA's
own chart labels: prices Rs per quintal, quantities tonnes.
"""
import json
import urllib.request

BASE = "https://agmarknet.ceda.ashoka.edu.in/api/"
COMMODITY_IDS = {"tomato": 78, "onion": 23}


def _post(endpoint, body):
    req = urllib.request.Request(BASE + endpoint, data=json.dumps(body).encode(),
                                 headers={"Content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def fetch_raw(crop, state_id, district_id, start, end):
    """Raw daily price and quantity responses for one district."""
    body = {"state_id": state_id, "commodity_id": COMMODITY_IDS[crop], "district_id": district_id,
            "calculation_type": "d", "start_date": start, "end_date": end}
    return {"request": body, "prices": _post("prices", body), "quantities": _post("quantities", body)}


def normalise(raw, market_id, crop):
    """Rows of {date, market_id, crop, arrivals_t, min/max/modal_price_kg, source}.

    Days with only a price or only a quantity keep the missing field as None; missing days stay absent.
    """
    rows = {}
    for p in raw["prices"]["data"]:
        rows[p["t"]] = {"date": p["t"], "market_id": market_id, "crop": crop, "arrivals_t": None,
                        "min_price_kg": p["p_min"] / 100, "max_price_kg": p["p_max"] / 100,
                        "modal_price_kg": p["p_modal"] / 100, "source": "ceda_agmarknet"}
    for q in raw["quantities"]["data"]:
        row = rows.setdefault(q["t"], {"date": q["t"], "market_id": market_id, "crop": crop,
                                       "min_price_kg": None, "max_price_kg": None,
                                       "modal_price_kg": None, "source": "ceda_agmarknet"})
        row["arrivals_t"] = q["qty"]
    return [rows[d] for d in sorted(rows)]

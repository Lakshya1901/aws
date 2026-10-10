"""Live mandi prices from Agmarknet 2.0 (CLAUDE.md D34).

Public endpoint, no key: GET https://api.agmarknet.gov.in/v1/prices-and-arrivals/commodity-price/lastweek gives one
market's prices for one commodity over the last 7 reported days (Rs/quintal; "NR" = not reported). It answers from
AWS ap-south-1 (checked October 10, 2026); agmarknet.gov.in refuses this repo's build network. Arrivals and the
state-wide reports need a captcha, so live data is prices only. Request headers follow the public site, as in
https://github.com/makrand999/agmarknet-api. Ids come from config (scripts/build_agmarknet_ids.py).
"""
import json
import urllib.parse
import urllib.request

URL = "https://api.agmarknet.gov.in/v1/prices-and-arrivals/commodity-price/lastweek"
HEADERS = {"Accept": "application/json, text/plain, */*", "Origin": "https://agmarknet.gov.in",
           "Referer": "https://agmarknet.gov.in/", "User-Agent": "Mozilla/5.0"}
QUINTAL = {"Rs./Quintal", "Rs/Quintal"}


def last_week(market_id, state_id, commodity_id, timeout=5):
    """[(date, modal_price_rs_per_kg)] for the reported days, oldest first; varieties averaged per day."""
    q = urllib.parse.urlencode({"marketId": market_id, "stateId": state_id, "commodityId": commodity_id,
                                "includeExcel": "false"})
    with urllib.request.urlopen(urllib.request.Request(f"{URL}?{q}", headers=HEADERS), timeout=timeout) as r:
        return parse(json.load(r))


def parse(body):
    """Rows of a last-week response -> [(date, Rs/kg)]; rows not priced per quintal are dropped, never converted."""
    days = [c["key"] for c in body.get("columns", []) if c["key"][:2] == "20"]
    out = []
    for d in sorted(days):
        vals = [row[d] for row in body.get("data", [])
                if row.get("unitOfPrice") in QUINTAL and isinstance(row.get(d), (int, float)) and row[d] > 0]
        if vals:
            out.append((d, sum(vals) / len(vals) / 100))
    return out

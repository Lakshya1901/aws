"""Add Agmarknet 2.0 ids to config/markets.json and config/commodities.json, for live prices (CLAUDE.md D34).
Run after scripts/build_idp_config.py, which rewrites both files.

The India Data Portal "New Source" file is Agmarknet 2.0 data: its market_center_code is the Agmarknet market id
(checked: 2,322 of 2,685 codes in the first 60 MB carry the same market name on agmarknet.gov.in). Our market_id
comes from the same file with build_idp.market_id, so the join is exact, never a fuzzy name match. The Agmarknet
state id of each market comes from Agmarknet's own filter list (GET https://api.agmarknet.gov.in/v1/daily-price-arrival/filters,
saved to a file: agmarknet.gov.in refuses this repo's build network but answers from AWS ap-south-1).
A commodity gets its Agmarknet id when its normalised Agmarknet name equals our crop_id (build_idp.slug), else none.

Usage: python scripts/build_agmarknet_ids.py --idp-new new.csv --filters filters.json [--config config]
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_idp import market_id, slug  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--idp-new", required=True)
    p.add_argument("--filters", required=True)
    p.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "..", "config"))
    a = p.parse_args()
    with open(a.filters, encoding="utf-8") as fh:
        f = json.load(fh)
    f = f.get("data", f)
    agm_state = {m["id"]: m["state_id"] for m in f["market_data"] if m.get("state_id")}
    codes = {}
    with open(a.idp_new, newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            if not (r.get("state_code") or "").isdigit() or not (r.get("market_center_code") or "").isdigit():
                continue
            code = int(r["market_center_code"])
            if code in agm_state:
                codes.setdefault(market_id(r["state_code"], r["market_center_name"]), set()).add(code)
    _write(os.path.join(a.config, "markets.json"), "markets", lambda m: _market(m, codes, agm_state))
    cmdt = {}
    for c in f["cmdt_data"]:
        cmdt.setdefault(slug(c["cmdt_name"]), []).append(c["cmdt_id"])
    _write(os.path.join(a.config, "commodities.json"), "commodities", lambda c: _commodity(c, cmdt))


def _market(m, codes, agm_state):
    c = codes.get(m["market_id"])
    m.pop("agmarknet", None)
    if c and len(c) == 1:  # two Agmarknet markets folded into one id: ambiguous, left out
        code = next(iter(c))
        m["agmarknet"] = {"market_id": code, "state_id": agm_state[code]}
    return "agmarknet" in m


def _commodity(c, cmdt):
    ids = cmdt.get(c["crop_id"])
    c.pop("agmarknet_id", None)
    if ids and len(ids) == 1:
        c["agmarknet_id"] = ids[0]
    return "agmarknet_id" in c


def _write(path, key, fill):
    """Fill each entry in place; keep the build_idp_config.py layout (one entry per line)."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    n = sum(fill(x) for x in doc[key])
    lines = ",\n".join("    " + json.dumps(x, ensure_ascii=False) for x in doc[key])
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('{\n  "_note": ' + json.dumps(doc["_note"]) + f',\n  "{key}": [\n' + lines + "\n  ]\n}\n")
    print(f"{n} of {len(doc[key])} {key} have Agmarknet ids")


if __name__ == "__main__":
    main()

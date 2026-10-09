"""Second replay day (CLAUDE.md Section 19.1 D10): an arrival-driven tomato glut, documented by dated news.

Usage: python analysis/second_replay.py [--snapshot data/snapshot/idp_tomato_2021-01-01_2026-05-31.csv.gz]

Writes analysis/out/second_replay.json. Deterministic: no timestamps; reuses analysis/backtest.py.

A day qualifies when, at market m:
  - arrival-driven: R >= watch_r (Section 9 Step 1; baseline from prior ISO years only),
  - price falls: 3-day dP <= watch_dp,
  - 7 of the last 7 days have price and arrivals at m and at the alternative,
  - an alternative within max_alt_km (straight line) pays >= min_gap_rs_kg and >= min_alt_ratio x m's modal price.
News evidence cannot be fetched reproducibly, so it is recorded below (DOCUMENTED) from manual reading,
with exact quotes. A candidate is accepted only if it qualifies in the data AND a dated article documents it.
"""
import argparse
import hashlib
import json
import pathlib

import pandas as pd

import backtest as bt

ROOT = bt.ROOT
OUT = bt.OUT

PARAMS = {
    "crop": "tomato",
    "max_alt_km": 200,
    "min_gap_rs_kg": 3.0,
    "min_alt_ratio": 1.25,
    "require_full_7_of_7": True,
}

# Manually verified news coverage (fetched 2026-10-08). Quotes are verbatim from the article text.
DOCUMENTED = [
    {
        "id": "kolar_2023_09",
        "market_id": "29-kolar",
        "news_attributes_to_arrivals": "yes",
        "window": ["2023-09-01", "2023-09-30"],
        "documented_by": [
            {
                "url": "https://www.freshplaza.com/asia/article/9556365/tomato-prices-down-at-kolar-market/",
                "title": "Tomato prices down at Kolar market (FreshPlaza, source: newindianexpress.com)",
                "date": "2023-09-04",
                "quote": "The prices fell drastically as the arrival of fresh produce caused a glut, while the demand in North India and Andhra Pradesh dropped in the last couple of weeks. [...] In the first week of July, a crate containing 15 kg of tomatoes was sold at Rs 2,400. Now, it has come down to Rs 100-240 (Rs 6-16 per kg). According to Deputy Director of Horticulture Kumaraswamy, the arrival of tomatoes has increased in the district.",
            },
            {
                "url": "https://www.deccanherald.com/india/karnataka/rs-200-to-rs-10-tomato-farmers-hopes-crash-2700660",
                "title": "Rs 200 to Rs 10: Tomato farmers' hopes crash (Deccan Herald)",
                "date": "2023-09-26",
                "quote": "The price crash is being attributed by officials from the Horticultural Department and the Agricultural Produce Market Committee (APMC) to the arrival of a large quantity of tomatoes and fall in demand from other states. [...] This month alone, the Kolar APMC, Asia's second-largest tomato market, received 4.21 lakh quintals of tomatoes. In the same period last year, the APMC received 2.31 lakh quintals [...] a box of 15 kg of tomatoes that was sold at Rs 2,300 in July and August is now being sold at Rs 45 to Rs 120. [...] many farmers in Kolar and surrounding areas have decided not to harvest the yield as the labour cost of harvesting is higher than the returns in the market.",
            },
        ],
    },
    {
        "id": "madanapalle_2024_12",
        "market_id": "28-madanapalli",
        "news_attributes_to_arrivals": "partly",
        "window": ["2024-12-01", "2024-12-26"],
        "documented_by": [
            {
                "url": "https://www.deccanchronicle.com/southern-states/andhra-pradesh/farmers-struggle-as-tomato-prices-plummet-1849854",
                "title": "Farmers struggle as tomato prices plummet (Deccan Chronicle)",
                "date": "2024-12-26",
                "quote": "Farmers of the erstwhile Chittoor district, particularly those from Madanapalle, Punganur and Palamaner regions, are shocked due to a dramatic plunge in tomato prices. Just weeks ago, a 15-kg crate of tomatoes fetched Rs 600 to Rs 900 in the wholesale market. Currently, it is selling for just Rs 200 to Rs 300. [...] The crisis surfaced when tomato exports to major consumer states, such as Tamil Nadu, Maharashtra, Gujarat, Kolkata and Delhi, stopped. [...] Further, tomatoes are also arriving from the neighbouring Anantapur district, pushing the fruit's prices further downward.",
            },
        ],
        "caveat": "The article gives demand loss (exports stopped) as the trigger; extra arrivals from Anantapur are a second factor.",
    },
    {
        "id": "kolar_2024_08",
        "market_id": "29-kolar",
        "news_attributes_to_arrivals": "no",
        "window": ["2024-08-01", "2024-08-31"],
        "documented_by": [
            {
                "url": "https://www.deccanherald.com/india/karnataka/tomato-exports-to-b-desh-stop-price-crash-hits-kolar-farmers-3152262",
                "title": "Tomato exports to Bangladesh stop, price crash hits farmers in Karnataka's Kolar (Deccan Herald)",
                "date": "2024-08-16",
                "quote": "At Kolar APMC, the prices of tomatoes crashed from Rs 40 a kg a fortnight ago to Rs 12 a kg. [...] Kolar APMC secretary Kiran Narayanswamy said, \"Around 40 to 50 trucks of tomatoes were being transported from Kolar to West Bengal every day before the first week of August. Now, the quantity has come down to 20 trucks a day.\"",
            },
        ],
        "caveat": "The article attributes the crash to lost demand (Bangladesh exports halted), not to higher arrivals.",
    },
    {
        "id": "madanapalle_2025_05_06",
        "market_id": "28-madanapalli",
        "window": ["2025-05-01", "2025-06-30"],
        "documented_by": None,
        "search_note": "Searched Deccan Herald, The Hindu, Times of India, New Indian Express, Hans India, Deccan Chronicle coverage of Madanapalle/Chittoor/Annamayya tomato prices for May-June 2025; no dated article documenting a glut at Madanapalle in that window was found.",
    },
    {
        "id": "kolar_2022_07",
        "market_id": "29-kolar",
        "window": ["2022-07-01", "2022-07-31"],
        "documented_by": None,
        "search_note": "No dated article for a July 2022 Kolar crash was found. R cannot be computed for 2022 anyway: the snapshot starts 2022-01-01, so there are no prior-year arrivals for the baseline.",
    },
]



def prior_years(arr_m, d):
    """ISO years that contribute arrivals to the baseline on date d (weeks w-1..w+1)."""
    iso = arr_m.index.isocalendar().astype("int64")
    y, w = int(d.isocalendar()[0]), int(d.isocalendar()[1])
    dist = (iso.week - w).abs()
    sel = (iso.year < y) & ((dist <= 1) | (dist >= 51)) & arr_m.notna().values
    return sorted({int(v) for v in iso.year[sel]})


def qualifying_days(m, window, arr, price, R, dP, level, full7, markets):
    th = bt.PARAMS["thresholds"]
    rows = []
    for d in pd.date_range(*window):
        if d not in R.index or not full7.at[d, m]:
            continue
        r, dp, p = R.at[d, m], dP.at[d, m], price.at[d, m]
        if not (r >= th["watch_r"] and dp <= th["watch_dp"]):
            continue
        best = None
        for o in price.columns:
            km = bt.haversine_km(markets[m], markets[o])
            if o == m or km > PARAMS["max_alt_km"] or not full7.at[d, o]:
                continue
            q = price.at[d, o]
            if q - p >= PARAMS["min_gap_rs_kg"] and q >= PARAMS["min_alt_ratio"] * p:
                if best is None or (q - p, o) > (best[0], best[1]):
                    best = (q - p, o, q, km)
        if best:
            rows.append((d, best))
    return rows


def day_record(d, m, best, arr, price, R, dP, B, level):
    gap, o, q, km = best
    a7 = arr[m].rolling(7, min_periods=bt.PARAMS["min_days_of_last_7"]).mean().at[d]
    return {
        "date": str(d.date()), "market_id": m,
        "R": bt.rnd(R.at[d, m], 2),
        "dP_3day": bt.rnd(dP.at[d, m], 3), "level": level.at[d, m],
        "modal_rs_kg": bt.rnd(price.at[d, m], 2), "modal_rs_kg_3_days_earlier": bt.rnd(price[m].shift(3).at[d], 2),
        "arrivals_t": bt.rnd(arr.at[d, m], 1), "arrivals_7day_mean_t": bt.rnd(a7, 1),
        "baseline_B_t": bt.rnd(B.at[d, m], 1), "baseline_prior_iso_years": prior_years(arr[m], d),
        "best_alternative": {"market_id": o, "modal_rs_kg": bt.rnd(q, 2), "gross_gap_rs_kg": bt.rnd(gap, 2),
                             "straight_line_km": bt.rnd(km, 1), "R": bt.rnd(R.at[d, o], 2), "level": level.at[d, o]},
        "completeness": {"market_7_of_7_days": True, "alternative_7_of_7_days": True},
    }


def main(snapshot):
    snap = pathlib.Path(snapshot) if snapshot else ROOT / "data/snapshot/idp_tomato_2021-01-01_2026-05-31.csv.gz"
    sha = hashlib.sha256(snap.read_bytes()).hexdigest()
    markets = {m["market_id"]: m for m in json.loads((ROOT / "config/markets.json").read_text())["markets"]}
    df = pd.read_csv(snap, parse_dates=["date"])
    df = df[(df.crop == PARAMS["crop"]) & df.market_id.isin(markets)]
    arr, price = bt.daily_tables(df)
    th = bt.PARAMS["thresholds"]
    R, dP, B, level = bt.risk(arr, price, th)
    full7 = (arr.notna() & price.notna()).rolling(7).sum() == 7

    # Data scan: every market-month with at least one qualifying day (not limited to documented windows).
    scan = []
    for m in price.columns:
        days = qualifying_days(m, [str(price.index[0].date()), str(price.index[-1].date())], arr, price, R, dP, level, full7, markets)
        by_month = {}
        for d, best in days:
            by_month.setdefault(str(d.to_period("M")), []).append((d, best))
        for mon, lst in sorted(by_month.items()):
            d, best = max(lst, key=lambda x: (x[1][0], -x[0].value))
            scan.append({"market_id": m, "month": mon, "qualifying_days": len(lst),
                         "best_day": str(d.date()), "best_alternative": best[1], "gross_gap_rs_kg": bt.rnd(best[0], 2),
                         "R": bt.rnd(R.at[d, m], 2), "modal_rs_kg": bt.rnd(price.at[d, m], 2)})

    cands = []
    for c in DOCUMENTED:
        m, w = c["market_id"], c["window"]
        days = qualifying_days(m, w, arr, price, R, dP, level, full7, markets)
        recs = [day_record(d, m, b, arr, price, R, dP, B, level) for d, b in days]
        recs.sort(key=lambda r: (-r["best_alternative"]["gross_gap_rs_kg"], r["date"]))
        ws = slice(*w)
        summary = {
            "R_median": bt.rnd(R[m][ws].median(), 2), "R_max": bt.rnd(R[m][ws].max(), 2),
            "R_days_known": int(R[m][ws].notna().sum()),
            "modal_rs_kg_min": bt.rnd(price[m][ws].min(), 2), "modal_rs_kg_median": bt.rnd(price[m][ws].median(), 2),
            "arrivals_t_median": bt.rnd(arr[m][ws].median(), 1), "baseline_B_t_median": bt.rnd(B[m][ws].median(), 1),
            "level_days": {k: int(v) for k, v in level[m][ws].value_counts().sort_index().items()},
            "price_days": int(price[m][ws].notna().sum()), "arrival_days": int(arr[m][ws].notna().sum()),
            "window_days": len(pd.date_range(*w)),
        }
        news_arr = c.get("news_attributes_to_arrivals")
        accepted = bool(recs) and c["documented_by"] is not None and news_arr in ("yes", "partly")
        if not recs and summary["R_days_known"] == 0:
            reason = "R not computable (no prior-year baseline in the snapshot)"
        elif not recs:
            reason = "no day meets all data criteria"
        elif c["documented_by"] is None:
            reason = "meets data criteria but no dated news article documents it"
        elif news_arr == "no":
            reason = "meets data criteria and is documented, but the news attributes the crash to lost demand, not arrivals"
        else:
            reason = "meets data criteria and is documented by dated news"
        cands.append({"id": c["id"], "market_id": m, "window": w, "window_summary": summary,
                      "qualifying_days_count": len(recs), "top_days": recs[:5],
                      "documented_by": c["documented_by"], "news_attributes_to_arrivals": news_arr, "caveat": c.get("caveat"), "search_note": c.get("search_note"),
                      "accepted": accepted, "reason": reason})

    # Recommendation: accepted candidate whose news ties the crash to arrivals outright first,
    # then most qualifying days, then largest gap.
    acc = [c for c in cands if c["accepted"]]
    acc.sort(key=lambda c: (c["news_attributes_to_arrivals"] != "yes", -c["qualifying_days_count"], -c["top_days"][0]["best_alternative"]["gross_gap_rs_kg"]))
    rec = None
    if acc:
        c = acc[0]
        rec = {"candidate_id": c["id"], "date": c["top_days"][0]["date"], "market_id": c["market_id"],
               "why": "largest gross gap among qualifying days in the best-documented arrival-driven glut"}
    for c in cands:
        c["recommended"] = rec is not None and c["id"] == rec["candidate_id"]

    results = {
        "snapshot": {"path": str(snap.relative_to(ROOT)), "sha256": sha, "source": "AGMARKNET market level, India Data Portal (D24)"},
        "params": PARAMS, "risk_thresholds": th,
        "criteria": "R >= watch_r (arrival-driven) and 3-day dP <= watch_dp (price falls) at the market; alternative within max_alt_km pays >= min_gap_rs_kg and >= min_alt_ratio x; 7 of last 7 days with price and arrivals at both markets; accepted only with a dated news source that ties the crash at least partly to arrivals",
        "gap_note": "gross modal price difference only; no freight, fees or spoilage",
        "observed_vs_model": "arrivals, prices, gaps and km are observed or computed from observed data; R and levels are model output",
        "candidates": cands,
        "recommended": rec,
        "scan_all_markets": scan,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "second_replay.json"
    out.write_text(json.dumps(results, indent=1, sort_keys=True) + "\n")
    print(out.relative_to(ROOT))
    return results


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot")
    main(p.parse_args().snapshot)

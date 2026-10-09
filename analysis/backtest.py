"""Backtest of the glut-risk rule (CLAUDE.md Section 9 Step 1, Section 17.2) on the market-level snapshot (D24).

Usage: python analysis/backtest.py --crop tomato [--snapshot data/snapshot/idp_tomato_2021-01-01_2026-05-31.csv.gz]

Crash scoring uses every market in the snapshot (markets within 350 km of the Kolar demo origin); price gaps and
the comparison chart use PARAMS["alternatives"].

Writes analysis/out/results_<run_id>.json and PNG charts. Deterministic: run_id is a hash of the
snapshot sha256 and PARAMS; the JSON has no timestamps.
"""
import argparse
import hashlib
import json
import math
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis/out"

PARAMS = {
    "default_market": "29-kolar",
    # Kolar-belt tomato markets with at least ~750 reported days in the snapshot (D24 market ids).
    "alternatives": ["29-chintamani", "29-srinivasapur", "29-mulabagilu", "29-bangarpet", "29-binnymillbengaluru",
                     "29-ramanagara", "28-madanapalli", "28-punganur", "28-kalikiri", "28-palamaner"],
    "thresholds": {"watch_r": 1.3, "glut_r": 2.0, "glut_r_with_dp": 1.5, "watch_dp": -0.15, "glut_dp": -0.25},
    "min_days_of_last_7": 5,
    "dp_days": 3,
    "crash_dp": -0.25,
    "harvest_cost_rs_per_kg": 4.7,
    "episode_merge_gap_days": 7,
    "lead_window_days": 7,
    "false_alarm_horizon_days": 7,
    "xcorr_lags": [1, 2, 3, 4, 5, 6, 7],
    "sweep_watch_r": [1.1, 1.2, 1.3, 1.5, 1.7, 2.0, 2.5, 3.0],
    "predictive_min_lead_days": 2,
    "glut_window": ["2025-01-01", "2025-04-30"],
    "chart_window": ["2024-12-01", "2025-05-31"],
}


def rnd(x, n=3):
    """Round for JSON; NaN/None become None."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), n)


def daily_tables(df):
    """Step 1: date x market tables for arrivals and modal price. Missing days stay NaN."""
    idx = pd.date_range(df.date.min(), df.date.max(), freq="D")
    arr = df.pivot(index="date", columns="market_id", values="arrivals_t").reindex(idx)
    price = df.pivot(index="date", columns="market_id", values="modal_price_kg").reindex(idx)
    return arr, price


def baseline(arr_m):
    """B: median arrivals in ISO weeks w-1..w+1 of prior ISO years only (weeks 52/53 wrap to 1)."""
    iso = arr_m.index.isocalendar().astype("int64")
    obs = pd.DataFrame({"y": iso.year.values, "w": iso.week.values, "a": arr_m.values}).dropna()
    out = pd.Series(np.nan, index=arr_m.index)
    for (y, w), days in pd.DataFrame({"y": iso.year.values, "w": iso.week.values}, index=arr_m.index).groupby(["y", "w"]):
        d = (obs.w - w).abs()
        prior = obs[(obs.y < y) & ((d <= 1) | (d >= 51))].a
        if len(prior):
            out[days.index] = prior.median()
    return out


def risk(arr, price, th):
    """Step 2: R, dP, completeness and level per market-day (Section 9 Step 1)."""
    n = PARAMS["min_days_of_last_7"]
    a7 = arr.rolling(7, min_periods=n).mean()
    B = arr.apply(baseline)
    R = a7 / B
    dP = price / price.shift(PARAMS["dp_days"]) - 1
    complete = arr.notna().rolling(7).sum().fillna(0) >= n
    level = level_of(R, dP, th).where(complete & R.notna(), "unknown")
    return R.where(complete), dP, B, level


def level_of(R, dP, th):
    glut = (R >= th["glut_r"]) | ((R > th["glut_r_with_dp"]) & (dP < th["glut_dp"]))
    watch = (R >= th["watch_r"]) | (dP < th["watch_dp"])
    return pd.DataFrame(np.select([glut, watch], ["glut", "watch"], "safe"), index=R.index, columns=R.columns)


def crash_days(price):
    """Step 4: modal price down > 25% in 3 days, or below harvest cost."""
    dP = price / price.shift(PARAMS["dp_days"]) - 1
    return ((dP < PARAMS["crash_dp"]) | (price < PARAMS["harvest_cost_rs_per_kg"])) & price.notna()


def episodes(crash_m):
    """Group a market's crash days; a new episode starts after more than merge_gap days without a crash."""
    days = list(crash_m[crash_m].index)
    eps = []
    for d in days:
        if eps and (d - eps[-1][-1]).days <= PARAMS["episode_merge_gap_days"]:
            eps[-1].append(d)
        else:
            eps.append([d])
    return eps


def lead_days(flag_m, known_m, start):
    """Step 5: days from the first flag in [start - window, start] to start; None if no flag, 'unscorable' if no data."""
    win = flag_m[start - pd.Timedelta(days=PARAMS["lead_window_days"]):start]
    if not known_m[win.index].any():
        return "unscorable"
    hit = win[win]
    return (start - hit.index[0]).days if len(hit) else None


def score(flags, known, crash):
    """Leads per crash episode and false-alarm flag days for one flag table."""
    eps, fa, nflag = [], 0, 0
    h = PARAMS["false_alarm_horizon_days"]
    for m in flags.columns:
        for e in episodes(crash[m]):
            eps.append({"market_id": m, "start": e[0], "lead": lead_days(flags[m], known[m], e[0])})
        fut = crash[m][::-1].rolling(h + 1, min_periods=1).max()[::-1].astype(bool)
        f = flags[m] & known[m]
        nflag += int(f.sum())
        fa += int((f & ~fut).sum())
    scored = [e for e in eps if e["lead"] != "unscorable"]
    leads = [e["lead"] for e in scored]
    early = sum(1 for x in leads if x is not None and x >= PARAMS["predictive_min_lead_days"])
    return {
        "episodes_total": len(eps), "episodes_scorable": len(scored),
        "flagged_in_window": sum(1 for x in leads if x is not None),
        "lead_ge_2_days": early,
        "share_lead_ge_2": rnd(early / len(scored)) if scored else None,
        "flag_days": nflag, "false_alarm_days": fa,
        "false_alarm_share": rnd(fa / nflag) if nflag else None,
    }, eps


def xcorr(R, price):
    """Step 3: Pearson correlation of R with forward k-day price change, pooled over markets."""
    rows = {}
    for k in PARAMS["xcorr_lags"]:
        fwd = price.shift(-k) / price - 1
        x, y = R.stack(), fwd.stack()
        j = pd.concat([x, y], axis=1, keys=["r", "f"]).dropna()
        per = {}
        for m in R.columns:
            jm = pd.concat([R[m], fwd[m]], axis=1, keys=["r", "f"]).dropna()
            per[m] = rnd(jm.r.corr(jm.f)) if len(jm) > 30 else None
        rows[k] = {"pooled_corr": rnd(j.r.corr(j.f)), "n": len(j), "per_market": per}
    best = min(rows, key=lambda k: rows[k]["pooled_corr"])
    return {"by_lag_days": rows, "strongest_negative_lag_days": best, "strongest_negative_corr": rows[best]["pooled_corr"],
            "note": "a glut signal that leads price would show clearly negative correlation; values near 0 or positive mean R does not lead price"}


def top_days(cands, price, arr, R, level, markets, K, keep, n=3):
    """Best alternative per date, top n dates by gross gap, among dates passing keep(date)."""
    seen, out = set(), []
    for gap, d, m in cands:
        if d in seen or not keep(d):
            continue
        seen.add(d)
        out.append({"date": str(d.date()), "alternative": m, "gross_gap_rs_kg": rnd(gap, 2),
                    "kolar": {"modal_rs_kg": rnd(price.at[d, K], 2), "arrivals_t": rnd(arr.at[d, K], 1),
                              "R": rnd(R.at[d, K], 2), "level": level.at[d, K]},
                    "alt": {"modal_rs_kg": rnd(price.at[d, m], 2), "arrivals_t": rnd(arr.at[d, m], 1),
                            "R": rnd(R.at[d, m], 2), "level": level.at[d, m]},
                    "straight_line_km": rnd(haversine_km(markets[K], markets[m]), 1)})
        if len(out) == n:
            break
    return out


def haversine_km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def main(crop, snapshot):
    snap = pathlib.Path(snapshot) if snapshot else ROOT / f"data/snapshot/idp_{crop}_2021-01-01_2026-05-31.csv.gz"
    sha = hashlib.sha256(snap.read_bytes()).hexdigest()
    run_id = hashlib.sha256((sha + json.dumps(PARAMS, sort_keys=True)).encode()).hexdigest()[:12]
    markets = {m["market_id"]: m for m in json.loads((ROOT / "config/markets.json").read_text())["markets"]}
    df = pd.read_csv(snap, parse_dates=["date"])
    df = df[(df.crop == crop) & df.market_id.isin(markets)]
    arr, price = daily_tables(df)
    th = PARAMS["thresholds"]
    R, dP, B, level = risk(arr, price, th)
    known = level != "unknown"
    crash = crash_days(price)
    K = PARAMS["default_market"]
    alts = [m for m in PARAMS["alternatives"] if m in price.columns]

    # Step 5: leads with the full rule, and with arrival-only flags (Section 7 asks whether arrivals lead price).
    full_score, full_eps = score(level.isin(["watch", "glut"]), known, crash)
    arr_score, arr_eps = score(R >= th["watch_r"], known, crash)
    ep_rows = [{"market_id": a["market_id"], "start": str(a["start"].date()),
                "lead_any_flag_days": a["lead"], "lead_arrival_flag_days": b["lead"],
                "price_kg_at_start": rnd(price.at[a["start"], a["market_id"]], 2),
                "R_at_start": rnd(R.at[a["start"], a["market_id"]], 2)}
               for a, b in zip(full_eps, arr_eps)]

    # Step 7: sweep the arrival-ratio watch threshold.
    sweep = []
    for w in PARAMS["sweep_watch_r"]:
        s, _ = score(R >= w, known, crash)
        sweep.append({"watch_r": w, **s})

    # Step 6: gross modal price gap (alternative minus Kolar) on Kolar crash days. Observed prices only.
    kc = crash[K][crash[K]].index
    gaps = {}
    for m in alts:
        g = (price.loc[kc, m] - price.loc[kc, K]).dropna()
        gaps[m] = {"crash_days_with_both_prices": len(g), "median_gap_rs_kg": rnd(g.median(), 2),
                   "share_days_alt_higher": rnd((g > 0).mean()) if len(g) else None,
                   "straight_line_km_from_kolar": rnd(haversine_km(markets[K], markets[m]), 1)}
    alt_pays = any((v["median_gap_rs_kg"] or 0) > 0 for v in gaps.values())

    # Glut check: Kolar Jan-Apr 2025 vs same months of prior years and vs alternatives.
    g0, g1 = PARAMS["glut_window"]
    months = [1, 2, 3, 4]
    kp = price[K]
    same_months = {str(y): rnd(kp[(kp.index.year == y) & kp.index.month.isin(months)].median(), 2) for y in (2021, 2022, 2023, 2024, 2025, 2026)}
    same_months_arr = {str(y): rnd(arr[K][(arr.index.year == y) & arr.index.month.isin(months)].median(), 1) for y in (2021, 2022, 2023, 2024, 2025, 2026)}
    win = slice(g0, g1)
    glut_check = {
        "window": [g0, g1],
        "kolar_median_modal_rs_kg_jan_apr_by_year": same_months,
        "kolar_median_arrivals_t_jan_apr_by_year": same_months_arr,
        "kolar_min_modal_rs_kg": rnd(kp[win].min(), 2), "kolar_min_modal_date": str(kp[win].idxmin().date()),
        "kolar_days_below_harvest_cost": int((kp[win] < PARAMS["harvest_cost_rs_per_kg"]).sum()),
        "kolar_price_days": int(kp[win].notna().sum()),
        "alt_median_modal_rs_kg": {m: rnd(price[m][win].median(), 2) for m in alts},
        "kolar_crash_episode_starts": [e["start"] for e in ep_rows if e["market_id"] == K and g0 <= e["start"] <= g1],
    }
    glut_model = {
        "kolar_median_R": rnd(R[K][win].median(), 2),
        "kolar_max_R": rnd(R[K][win].max(), 2),
        "kolar_level_days": {k: int(v) for k, v in level[K][win].value_counts().sort_index().items()},
        "kolar_episode_leads": [e for e in ep_rows if e["market_id"] == K and g0 <= e["start"] <= g1],
    }

    # Demo day: Kolar glut window, largest gap to an alternative, all 7 of last 7 days present for both markets.
    full7 = (arr.notna() & price.notna()).rolling(7).sum() == 7
    cands = []
    for d in pd.date_range(g0, g1):
        if not full7.at[d, K]:
            continue
        for m in alts:
            if full7.at[d, m]:
                cands.append((round(price.at[d, m] - price.at[d, K], 4), d, m))
    cands.sort(key=lambda c: (-c[0], c[1], c[2]))
    demo = top_days(cands, price, arr, R, level, markets, K, lambda d: True)
    demo_flagged = top_days(cands, price, arr, R, level, markets, K, lambda d: level.at[d, K] in ("watch", "glut"))

    xc = xcorr(R, price)
    share = arr_score["share_lead_ge_2"]
    mode = "predictive" if share is not None and share > 0.5 and alt_pays else "same_day"

    results = {
        "run_id": run_id, "crop": crop,
        "observed": {
            "snapshot": {"path": str(snap.relative_to(ROOT)), "sha256": sha, "source": "AGMARKNET market level, India Data Portal (D24)"},
            "coverage_days": {m: {"price": int(price[m].notna().sum()), "arrivals": int(arr[m].notna().sum())} for m in price.columns},
            "kolar_2025_glut_check": glut_check,
            "crash_days_per_market": {m: int(crash[m].sum()) for m in crash.columns},
            "crash_episodes": [{k: e[k] for k in ("market_id", "start", "price_kg_at_start")} for e in ep_rows],
            "kolar_crash_day_gross_price_gap_vs_alternatives": gaps,
        },
        "model": {
            "note": "R, risk levels, flags and leads are model output from the Section 9 Step 1 rule on observed data.",
            "kolar_2025_glut_window": glut_model,
            "crash_episode_leads": ep_rows,
            "xcorr_R_vs_forward_price_change": xc,
            "lead_full_rule": full_score,
            "lead_arrival_ratio_only": arr_score,
            "threshold_sweep_arrival_ratio": sweep,
        },
        "assumptions": {
            "params": PARAMS,
            "harvest_cost_source": "Rs 70 per 15 kg box, Kolar 2025, Outlook Business (CLAUDE.md Section 10); sourced",
            "thresholds_source": "CLAUDE.md Section 9 Step 1 defaults",
            "lead_definition": "days from the earliest flag within lead_window_days before an episode's first crash day; 0 = same day; null = no flag",
            "false_alarm_definition": "flag day with no crash day in the same market within false_alarm_horizon_days",
            "week_adjacency": "ISO weeks w-1..w+1 with 52/53 adjacent to 1",
            "demo_gap": "gross modal price difference only; no freight, fees or spoilage applied",
        },
        "simulated": {},
        "mode_recommendation": {
            "mode": mode,
            "rule": "predictive only if arrival-ratio flags lead crash episodes by >= 2 days on most (>50%) scorable episodes and an alternative pays; else same_day (CLAUDE.md Sections 7, 17.2)",
            "share_episodes_arrival_lead_ge_2": share,
            "share_episodes_any_flag_lead_ge_2": full_score["share_lead_ge_2"],
            "strongest_negative_lag_days": xc["strongest_negative_lag_days"],
            "strongest_negative_corr": xc["strongest_negative_corr"],
            "alternative_pays_gross": alt_pays,
        },
        "demo_day": {"criteria": "Kolar Jan-Apr 2025; 7 of last 7 days with price and arrivals for Kolar and the alternative; largest gross modal gap",
                     "candidates": demo,
                     "candidates_kolar_flagged_watch_or_glut": demo_flagged},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"results_{run_id}.json"
    out.write_text(json.dumps(results, indent=1, sort_keys=True) + "\n")
    charts(price, arr, R, level, K, alts, demo, {m: markets[m]["name"] for m in [K] + alts})
    print(out.relative_to(ROOT))
    return results


def charts(price, arr, R, level, K, alts, demo, names):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; charts skipped")
        return
    c0, c1 = PARAMS["chart_window"]
    w = slice(c0, c1)
    meta = {"Software": None}
    colors = {"watch": "#f2c14e", "glut": "#d1495b"}

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    a1.plot(price[K][w].index, price[K][w], color="#222", lw=1.5, label="Kolar modal price (observed)")
    a1.axhline(PARAMS["harvest_cost_rs_per_kg"], color="#888", ls="--", lw=1, label="Harvest + transport cost Rs 4.7/kg (sourced)")
    a1.set_ylabel("Rs/kg")
    a1.legend(loc="upper right", fontsize=8, frameon=False)
    a2.plot(R[K][w].index, R[K][w], color="#2e86ab", lw=1.5, label="Arrival ratio R (model)")
    for lv, c in colors.items():
        days = level[K][w][level[K][w] == lv].index
        for ax in (a1, a2):
            ax.scatter(days, [ax.get_ylim()[0]] * len(days), color=c, marker="|", s=80, label=None)
        a2.scatter([], [], color=c, marker="|", label=f"{lv} flag (model)")
    a2.axhline(PARAMS["thresholds"]["watch_r"], color="#f2c14e", ls=":", lw=1)
    a2.axhline(PARAMS["thresholds"]["glut_r"], color="#d1495b", ls=":", lw=1)
    a2.set_ylabel("R = A7 / B")
    a2.legend(loc="upper left", fontsize=8, frameon=False)
    a1.set_title("Kolar tomato, Dec 2024 - May 2025 (AGMARKNET market data, India Data Portal)")
    fig.tight_layout()
    fig.savefig(OUT / "kolar_glut_2025.png", dpi=130, metadata=meta)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    roll = price[w].rolling(7, min_periods=5).mean()
    for m in alts:
        ax.plot(roll.index, roll[m], lw=1, alpha=0.8, label=names[m])
    ax.plot(roll.index, roll[K], lw=2.5, color="#222", label="Kolar")
    for c in demo:
        ax.axvline(pd.Timestamp(c["date"]), color="#d1495b", lw=0.8, ls=":")
    ax.set_ylabel("Modal price, Rs/kg (7-day mean, observed)")
    ax.set_title("Kolar vs alternative markets, tomato (dotted: demo-day candidates)")
    ax.legend(fontsize=8, ncol=4, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "kolar_vs_alternatives_2025.png", dpi=130, metadata=meta)
    plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--crop", required=True)
    p.add_argument("--snapshot")
    a = p.parse_args()
    main(a.crop, a.snapshot)

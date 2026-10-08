"""Step 1: glut risk per market (CLAUDE.md Section 9)."""
from datetime import date, timedelta
from statistics import median

from .config import assumption


def to_date(d):
    return d if isinstance(d, date) else date.fromisoformat(d)


def by_date(rows, as_of_date):
    """Index one market's rows by date, dropping rows after as_of_date (no look-ahead)."""
    as_of = to_date(as_of_date)
    out = {}
    for r in rows:
        d = to_date(r["date"])
        if d <= as_of:
            out[d] = r
    return out


def baseline(rows_by_date, anchor):
    """B: median arrivals over ISO weeks w-1..w+1 of every prior ISO year in the data."""
    iso_year, week, _ = anchor.isocalendar()
    years = {d.isocalendar()[0] for d in rows_by_date}
    vals = []
    for y in sorted(years):
        if y >= iso_year:
            continue
        wk = min(week, date(y, 12, 28).isocalendar()[1])  # week 53 -> 52 in 52-week years
        start = date.fromisocalendar(y, wk, 1) - timedelta(days=7)
        for i in range(21):
            r = rows_by_date.get(start + timedelta(days=i))
            if r and r.get("arrivals_t") is not None:
                vals.append(r["arrivals_t"])
    return median(vals) if vals else None


def risk_level(ratio, price_change_3d, thresholds):
    """safe / watch / glut per the Section 9 table; None when the ratio is unknown."""
    if ratio is None:
        return None
    dp = price_change_3d
    if ratio >= thresholds["glut_ratio"] or (
            ratio > thresholds["glut_combo_ratio"] and dp is not None
            and dp < thresholds["glut_combo_price_change_3d"]):
        return "glut"
    if ratio >= thresholds["watch_ratio"] or (dp is not None and dp < thresholds["watch_price_change_3d"]):
        return "watch"
    return "safe"


def market_risk(rows, as_of_date, model, assumptions):
    """Risk for one market from its rows [{date, market_id, arrivals_t, modal_price_kg}].

    The 7-day window ends at the market's latest reported date on or before as_of_date.
    Returns None if the market has no rows.
    """
    idx = by_date(rows, as_of_date)
    if not idx:
        return None
    as_of = to_date(as_of_date)
    latest = max(idx)
    window = [idx.get(latest - timedelta(days=i)) for i in range(7)]
    arrivals = [r["arrivals_t"] for r in window if r and r.get("arrivals_t") is not None]
    data_complete = len(arrivals) >= model["min_days_of_last_7"]
    base = baseline(idx, latest)
    a7 = sum(arrivals) / len(arrivals) if arrivals else None
    ratio = a7 / base if data_complete and base else None
    price = idx[latest].get("modal_price_kg")
    prev = idx.get(latest - timedelta(days=3))
    prev_price = prev.get("modal_price_kg") if prev else None
    dp = (price - prev_price) / prev_price if price is not None and prev_price else None
    return {
        "market_id": idx[latest]["market_id"],
        "as_of_date": as_of.isoformat(),
        "latest_date": latest.isoformat(),
        "stale": (as_of - latest).days > assumption(assumptions, "stale_days"),
        "data_complete": data_complete,
        "days_of_last_7": len(arrivals),
        "a7_t": a7,
        "a7_sum_t": sum(arrivals),
        "baseline_t": base,
        "arrival_ratio": ratio,
        "price_kg": price,
        "arrivals_t": idx[latest].get("arrivals_t"),
        "price_change_3d": dp,
        "risk_level": risk_level(ratio, dp, model["risk"]),
    }


def projected_ratio(risk, added_t):
    """Projected R: A7 recomputed with today's arrivals plus added_t tonnes, divided by B."""
    if risk["arrival_ratio"] is None:
        return None
    return (risk["a7_sum_t"] + added_t) / risk["days_of_last_7"] / risk["baseline_t"]

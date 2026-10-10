"""Step 2: price on arrival, including AnnaSetu's own loads (CLAUDE.md Section 9)."""
from math import exp, log, sqrt

from .risk import by_date


def fit_elasticity(rows, as_of_date, model):
    """Fit b by OLS of ln(price) on ln(arrivals) over the market's history up to as_of_date.

    b is clipped to the configured range; if R^2 < r2_min (or the fit is degenerate) the fallback b
    is used. resid_sd (D15) is the standard deviation of day-to-day changes in ln(modal price) between
    reported days at most max_gap_days apart: the uncertainty of selling at today's price on arrival.
    Fewer than 3 such changes -> resid_sd None.
    """
    cfg = model["elasticity"]
    pts = [(log(r["arrivals_t"]), log(r["modal_price_kg"])) for r in by_date(rows, as_of_date).values()
           if r.get("arrivals_t") and r.get("modal_price_kg") and r["arrivals_t"] > 0 and r["modal_price_kg"] > 0]
    n = len(pts)
    resid_sd = price_change_sd(rows, as_of_date, cfg["range_max_gap_days"])
    if n < 3:
        return {"b": cfg["fallback_b"], "r2": None, "resid_sd": resid_sd, "n": n, "b_source": "fallback"}
    mx = sum(x for x, _ in pts) / n
    my = sum(y for _, y in pts) / n
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    syy = sum((y - my) ** 2 for _, y in pts)
    sxy = sum((x - mx) * (y - my) for x, y in pts)
    r2 = sxy * sxy / (sxx * syy) if sxx > 0 and syy > 0 else 0.0
    if sxx == 0 or r2 < cfg["r2_min"]:
        b, source = cfg["fallback_b"], "fallback"
    else:
        lo, hi = cfg["clip"]
        b_ols = sxy / sxx
        b = min(hi, max(lo, b_ols))
        source = "fit" if b == b_ols else "clipped"
    return {"b": b, "r2": r2, "resid_sd": resid_sd, "n": n, "b_source": source}


def price_change_sd(rows, as_of_date, max_gap_days):
    """SD of ln(P_t / P_prev) over consecutive reported days at most max_gap_days apart."""
    days = sorted((d, log(r["modal_price_kg"])) for d, r in by_date(rows, as_of_date).items()
                  if r.get("modal_price_kg") and r["modal_price_kg"] > 0)
    ch = [y2 - y1 for (d1, y1), (d2, y2) in zip(days, days[1:]) if (d2 - d1).days <= max_gap_days]
    if len(ch) < 3:
        return None
    m = sum(ch) / len(ch)
    return sqrt(sum((c - m) ** 2 for c in ch) / (len(ch) - 1))


def price_on_arrival(price_kg, arrivals_t, added_t, b, resid_sd, sd_multiplier=1.0):
    """P_hat = P * ((A + dA) / A) ^ b, with range = P_hat * exp(+/- k * resid_sd) (log space).

    sd_multiplier k is 1, or the stale multiplier when the market's data is stale.
    Live prices without arrivals (D34): arrivals_t None, so P_hat = P (our own loads' effect can't be computed).
    """
    mid = price_kg if arrivals_t is None else price_kg * ((arrivals_t + added_t) / arrivals_t) ** b
    k = sd_multiplier * resid_sd
    return {"low": mid * exp(-k), "mid": mid, "high": mid * exp(k)}

"""Step 2: price on arrival, including AnnaSetu's own loads (CLAUDE.md Section 9)."""
from math import exp, log, sqrt

from .risk import by_date


def fit_elasticity(rows, as_of_date, model):
    """Fit b by OLS of ln(price) on ln(arrivals) over the market's history up to as_of_date.

    b is clipped to the configured range; if R^2 < r2_min (or the fit is degenerate) the fallback b
    is used. resid_sd is the residual standard deviation (log space) of the b actually used, with
    the intercept refitted for that b. Fewer than 3 points -> resid_sd None.
    """
    cfg = model["elasticity"]
    pts = [(log(r["arrivals_t"]), log(r["modal_price_kg"])) for r in by_date(rows, as_of_date).values()
           if r.get("arrivals_t") and r.get("modal_price_kg") and r["arrivals_t"] > 0 and r["modal_price_kg"] > 0]
    n = len(pts)
    if n < 3:
        return {"b": cfg["fallback_b"], "r2": None, "resid_sd": None, "n": n, "b_source": "fallback"}
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
    a = my - b * mx
    resid_sd = sqrt(sum((y - a - b * x) ** 2 for x, y in pts) / (n - 2))
    return {"b": b, "r2": r2, "resid_sd": resid_sd, "n": n, "b_source": source}


def price_on_arrival(price_kg, arrivals_t, added_t, b, resid_sd, sd_multiplier=1.0):
    """P_hat = P * ((A + dA) / A) ^ b, with range = P_hat * exp(+/- k * resid_sd) (log space).

    sd_multiplier k is 1, or the stale multiplier when the market's data is stale.
    """
    mid = price_kg * ((arrivals_t + added_t) / arrivals_t) ** b
    k = sd_multiplier * resid_sd
    return {"low": mid * exp(-k), "mid": mid, "high": mid * exp(k)}

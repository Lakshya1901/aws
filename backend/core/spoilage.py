"""Step 3: spoilage on the trip, no sensors (CLAUDE.md Section 9)."""


def shelf_life_hours(temp_c, sl_ref_hours, q10, t_ref_c):
    """SL(T) = SL_ref * Q10 ^ (-(T - T_ref) / 10)."""
    return sl_ref_hours * q10 ** (-(temp_c - t_ref_c) / 10)


def spoilage_share(hours, temp_c, crop):
    """s = min(1, alpha * hours / SL(T)) for hours = t_since_harvest + t_drive + t_wait.

    Range: low uses the long end of sl_ref_hours_range, high the short end, mid sl_ref_hours.
    """
    def s(sl_ref):
        return min(1.0, crop["alpha"] * hours / shelf_life_hours(temp_c, sl_ref, crop["q10"], crop["t_ref_c"]))
    short, long_ = crop["sl_ref_hours_range"]
    return {"low": s(long_), "mid": s(crop["sl_ref_hours"]), "high": s(short)}

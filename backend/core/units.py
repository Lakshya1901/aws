"""Unit conversions (CLAUDE.md Sections 8.2 and 12)."""

KG_PER = {"kg": 1, "quintal": 100, "tonne": 1000}


def price_quintal_to_kg(rs_per_quintal):
    """Rs per quintal -> Rs per kg."""
    return None if rs_per_quintal is None else rs_per_quintal / 100


def quantity_to_kg(quantity, unit, crop=None):
    """Convert kg, quintal, tonne or box (crop's unit_box_kg) to kg."""
    if unit == "box":
        box = (crop or {}).get("unit_box_kg")
        if box is None:
            raise ValueError("Box size unknown for this crop")
        return quantity * box
    return quantity * KG_PER[unit]

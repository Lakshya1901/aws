"""Load and validate config JSON (CLAUDE.md Sections 9-11). Standard library only."""
import json
import os

REQUIRED_CROP_FIELDS = (
    "crop_id", "t_ref_c", "sl_ref_hours", "sl_ref_hours_range", "q10", "alpha",
    "storable", "second_life",
)


class CoreError(Exception):
    """Error the API layer maps to an HTTP status (422 for the codes below).

    Codes: crop_profile_incomplete, no_markets_in_radius, drive_time_unavailable.
    """

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_crop(profile):
    """Return the profile if every required field is non-null, else raise crop_profile_incomplete."""
    missing = [f for f in REQUIRED_CROP_FIELDS if profile.get(f) is None]
    if missing:
        crop = profile.get("crop_id") or "unknown"
        raise CoreError("crop_profile_incomplete",
                        f"Crop profile '{crop}' is incomplete: null or missing {', '.join(missing)}")
    return profile


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_configs(config_dir):
    """Read config/ into one dict.

    Returns {"model", "assumptions", "crops": {crop_id: profile}, "crop_errors": {crop_id: message},
    "outlets": [...], "markets": [...], "commodities": {crop_id: entry}} . Incomplete crop profiles land in crop_errors, never in crops.
    """
    crops, crop_errors = {}, {}
    crop_dir = os.path.join(config_dir, "crops")
    for name in sorted(os.listdir(crop_dir)):
        if not name.endswith(".json"):
            continue
        profile = _read(os.path.join(crop_dir, name))
        crop_id = profile.get("crop_id") or name[:-5]
        try:
            crops[crop_id] = validate_crop(profile)
        except CoreError as e:
            crop_errors[crop_id] = e.message
    markets_path = os.path.join(config_dir, "markets.json")
    markets = _read(markets_path)["markets"] if os.path.exists(markets_path) else []
    commodities_path = os.path.join(config_dir, "commodities.json")
    commodities = _read(commodities_path)["commodities"] if os.path.exists(commodities_path) else []
    return {
        "model": _read(os.path.join(config_dir, "model.json")),
        "assumptions": _read(os.path.join(config_dir, "assumptions.json")),
        "crops": crops,
        "crop_errors": crop_errors,
        "outlets": _read(os.path.join(config_dir, "outlets.json"))["outlets"],
        "markets": markets,
        "commodities": {c["crop_id"]: c for c in commodities},
    }


def get_crop(configs, crop_id):
    """Return a validated crop profile or raise crop_profile_incomplete."""
    if crop_id in configs["crops"]:
        return configs["crops"][crop_id]
    msg = configs.get("crop_errors", {}).get(crop_id, f"No crop profile for '{crop_id}'")
    raise CoreError("crop_profile_incomplete", msg)


def radar_crop(configs, crop_id):
    """Profile for the Glut Radar: the full crop profile, else a radar-only entry from config/commodities.json
    (D24: risk needs only prices and arrivals; routing still needs a complete profile)."""
    if crop_id in configs["crops"]:
        return configs["crops"][crop_id]
    c = configs.get("commodities", {}).get(crop_id)
    if c is None:
        return get_crop(configs, crop_id)
    return {"crop_id": crop_id, "names": {"en": c["name"]}, "unit_box_kg": None, "radar_only": True}


def assumption_entry(assumptions, key, state=None):
    """The assumption entry, with the per-state override merged in when one exists."""
    entry = assumptions[key]
    override = (entry.get("per_state") or {}).get(state) if state else None
    return {**entry, **override} if override else entry


def assumption(assumptions, key, state=None):
    """The assumption value for key (per-state override if any)."""
    return assumption_entry(assumptions, key, state)["value"]


def crop_mode(model, crop_id):
    return model.get("mode", {}).get(crop_id) or model.get("default_mode", "same_day")

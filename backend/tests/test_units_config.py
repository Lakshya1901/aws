import copy

import pytest

from backend.core.config import CoreError, assumption, load_configs, validate_crop
from backend.core.recommend import recommend
from backend.core.units import price_quintal_to_kg, quantity_to_kg
from backend.tests.fixtures import AS_OF, CONFIG_DIR, MARKETS, OUTLETS, load, normal_week


def test_price_rs_per_quintal_to_rs_per_kg():
    assert price_quintal_to_kg(2000) == 20
    assert price_quintal_to_kg(None) is None


def test_boxes_quintals_tonnes_to_kg(configs):
    tomato = configs["crops"]["tomato"]
    assert quantity_to_kg(10, "box", tomato) == 150
    assert quantity_to_kg(3, "quintal") == 300
    assert quantity_to_kg(2, "tonne") == 2000


def test_box_without_box_size_is_rejected(configs):
    with pytest.raises(ValueError):
        quantity_to_kg(1, "box", {"unit_box_kg": None})


def test_null_crop_field_rejected():
    c = load_configs(CONFIG_DIR)
    assert {"tomato", "onion", "potato", "banana"} <= set(c["crops"]) and not c["crop_errors"]  # D33: 50 profiles
    with pytest.raises(CoreError) as e:
        validate_crop(dict(c["crops"]["tomato"], alpha=None))
    assert e.value.code == "crop_profile_incomplete" and "alpha" in e.value.message
    assert validate_crop(dict(c["crops"]["tomato"], harvest_cost_rs_per_kg=None))  # optional since D33


def test_recommend_with_incomplete_crop_raises_422_code(configs):
    with pytest.raises(CoreError) as e:
        recommend(load(crop="jack_fruit"), normal_week(), MARKETS, OUTLETS, configs, AS_OF)  # no profile
    assert e.value.code == "crop_profile_incomplete"


def test_assumption_per_state_override(configs):
    a = configs["assumptions"]
    assert assumption(a, "fee_pct", "KA") == 0.0
    assert assumption(a, "fee_pct", "AP") == 0.01
    assert assumption(a, "fee_pct", "MH") == 0.01
    assert assumption(a, "commission_pct", "AP") == 0.04
    assert assumption(a, "commission_pct") == 0.05


def test_every_assumption_has_status_and_source(configs):
    for key, entry in configs["assumptions"].items():
        if key.startswith("_"):
            continue
        assert entry["status"] in ("sourced", "assumption", "placeholder"), key
        assert entry["source"] and "unit" in entry and "value" in entry, key


def test_drive_time_unavailable_without_route_or_speed(configs):
    c = copy.deepcopy(configs)
    c["assumptions"]["truck_speed_kmph"]["value"] = None
    with pytest.raises(CoreError) as e:
        recommend(load(), normal_week(), MARKETS, OUTLETS, c, AS_OF)
    assert e.value.code == "drive_time_unavailable"

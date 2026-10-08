import copy

import pytest

from backend.core.config import load_configs
from backend.tests.fixtures import CONFIG_DIR


@pytest.fixture
def configs():
    c = copy.deepcopy(load_configs(CONFIG_DIR))
    # Test-only value: the real config leaves truck_speed_kmph null until it is sourced.
    c["assumptions"]["truck_speed_kmph"]["value"] = 40
    return c

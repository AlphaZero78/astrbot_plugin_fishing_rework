from __future__ import annotations

from types import SimpleNamespace

import pytest

from astrbot_plugin_fishing.core.mechanics import (
    bait_cost_per_attempt,
    consumes_bait_per_attempt,
)


def test_non_consumable_bait_is_not_charged_per_attempt():
    bait = SimpleNamespace(
        is_consumable=False, duration_minutes=0, cost=1000
    )
    assert consumes_bait_per_attempt(bait) is False
    assert bait_cost_per_attempt(bait, 180) == 0


def test_timed_bait_cost_is_amortized_over_covered_attempts():
    bait = SimpleNamespace(
        is_consumable=True, duration_minutes=30, cost=250
    )
    assert consumes_bait_per_attempt(bait) is False
    assert bait_cost_per_attempt(bait, 180) == pytest.approx(25)


def test_single_use_bait_is_consumed_and_charged_once():
    bait = SimpleNamespace(is_consumable=True, duration_minutes=0, cost=30)
    assert consumes_bait_per_attempt(bait) is True
    assert bait_cost_per_attempt(bait, 180) == 30

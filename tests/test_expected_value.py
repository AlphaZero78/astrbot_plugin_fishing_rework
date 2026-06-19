from __future__ import annotations

import math

import pytest

from astrbot_plugin_fishing.core.analytics.expected_value import (
    FishingScenario,
    GachaEntry,
    apply_rare_bonus,
    expected_fishing_return,
    expected_gacha_return,
    quality_bonus_chance,
    weighted_fish_value,
)


def test_rare_bonus_preserves_six_plus_bucket_and_total():
    original = [0.2, 0.3, 0.2, 0.2, 0.09, 0.01]
    adjusted = apply_rare_bonus(original, 0.25)

    assert sum(adjusted) == pytest.approx(1.0)
    assert adjusted[5] == pytest.approx(original[5])
    assert sum(adjusted[:3]) == pytest.approx(sum(original[:3]) * 0.75)


def test_quality_bonus_matches_runtime_logarithmic_formula():
    assert quality_bonus_chance(1.0, 0.35) == 0
    assert quality_bonus_chance(2.0, 0.35) == pytest.approx(0.175)
    assert quality_bonus_chance(4.0, 0.35) == pytest.approx(0.35)
    assert quality_bonus_chance(8.0, 0.35) == pytest.approx(0.35)


def test_weighted_fish_value_uses_base_value_as_weight():
    assert weighted_fish_value([10, 20]) == pytest.approx(50 / 3)
    assert weighted_fish_value([10, 20], 0) == pytest.approx(15)


def test_expected_fishing_return_combines_runtime_multipliers():
    values = {rarity: [rarity * 10] for rarity in range(1, 7)}
    result = expected_fishing_return(
        [1, 0, 0, 0, 0, 0],
        values,
        FishingScenario(
            success_rate=0.8,
            quantity_modifier=1.5,
            value_modifier=2.0,
            quality_modifier=4.0,
            quality_bonus_cap=0.4,
            fishing_cost=5,
        ),
    )

    assert result["quality_bonus_chance"] == pytest.approx(0.4)
    assert result["expected_catches"] == pytest.approx(1.2)
    assert result["gross_value"] == pytest.approx(33.6)
    assert result["net_value"] == pytest.approx(28.6)


def test_expected_fishing_return_ignores_empty_zero_probability_buckets():
    result = expected_fishing_return(
        [1, 0, 0, 0, 0, 0],
        {1: [10]},
    )
    assert result["gross_value"] == pytest.approx(7)


def test_expected_gacha_return_tracks_unknown_rewards():
    result = expected_gacha_return(
        [
            GachaEntry("coins", 0, 100, 1),
            GachaEntry("bait", 3, 2, 1),
            GachaEntry("title", 9, 1, 2),
        ],
        {("bait", 3): 50},
        draw_cost=80,
    )

    assert result["gross_value"] == pytest.approx(50)
    assert result["net_value"] == pytest.approx(-30)
    assert result["return_ratio"] == pytest.approx(0.625)
    assert result["unresolved_probability"] == pytest.approx(0.5)


def test_zero_cost_reports_infinite_return_ratio():
    result = expected_gacha_return(
        [GachaEntry("coins", 0, 10, 1)], {}, draw_cost=0
    )
    assert math.isinf(result["return_ratio"])

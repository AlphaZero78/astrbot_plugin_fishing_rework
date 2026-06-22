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
    weighted_fish_metrics,
)
from astrbot_plugin_fishing.core.mechanics import (
    expected_catch_count,
    high_rarity_weights,
    roll_catch_count,
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


def test_within_rarity_fish_selection_is_uniform():
    assert weighted_fish_value([10, 20]) == pytest.approx(15)
    assert weighted_fish_value([50, 500000, 1000000]) == pytest.approx(
        500016.6666666667
    )


def test_weighted_fish_metrics_tracks_garbage_probability():
    expected, probability, contribution = weighted_fish_metrics([1, 9])
    assert expected == pytest.approx(5)
    assert probability == pytest.approx(0.5)
    assert contribution == pytest.approx(0.5)


def test_garbage_reduction_models_one_reroll():
    result = expected_fishing_return(
        [1, 0, 0, 0, 0, 0],
        {1: [1, 9]},
        FishingScenario(success_rate=1, garbage_reduction=1),
    )
    # 5.0 + 50% * (5.0 - 1.0)
    assert result["expected_base_value_on_success"] == pytest.approx(7.0)


def test_high_rarity_weights_decay_by_half_per_star():
    weights = high_rarity_weights([8, 6, 7])
    assert weights == {6: 1.0, 7: 0.5, 8: 0.25}
    total = sum(weights.values())
    assert weights[6] / total == pytest.approx(4 / 7)
    assert weights[7] / total == pytest.approx(2 / 7)
    assert weights[8] / total == pytest.approx(1 / 7)


def test_expected_return_uses_decreasing_high_rarity_weights():
    result = expected_fishing_return(
        [0, 0, 0, 0, 0, 1],
        {
            6: [60],
            7: [700],
            8: [50, 500000, 1000000],
        },
        FishingScenario(success_rate=1),
    )
    expected_eight = (50 + 500000 + 1000000) / 3
    expected = 60 * 4 / 7 + 700 * 2 / 7 + expected_eight * 1 / 7
    assert result["expected_base_value_on_success"] == pytest.approx(expected)


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
    assert result["attempts_per_hour"] == pytest.approx(20)
    assert result["net_value_per_hour"] == pytest.approx(572)


def test_quantity_modifier_preserves_the_guaranteed_first_catch():
    assert expected_catch_count(0.5) == pytest.approx(1.0)
    assert roll_catch_count(0.5, lambda: 0.0) == 1
    assert roll_catch_count(1.3, lambda: 0.29) == 2
    assert roll_catch_count(1.3, lambda: 0.31) == 1

    result = expected_fishing_return(
        [1, 0, 0, 0, 0, 0],
        {1: [10]},
        FishingScenario(success_rate=1, quantity_modifier=0.5),
    )
    assert result["expected_catches"] == pytest.approx(1.0)
    assert result["gross_value"] == pytest.approx(10.0)


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

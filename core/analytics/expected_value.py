"""Deterministic expected-value calculations matching runtime game mechanics."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class FishingScenario:
    success_rate: float = 0.7
    quantity_modifier: float = 1.0
    value_modifier: float = 1.0
    quality_modifier: float = 1.0
    rare_bonus: float = 0.0
    quality_bonus_cap: float = 0.35
    fishing_cost: int = 0
    consumable_cost: float = 0.0
    cooldown_seconds: float = 180.0
    garbage_reduction: float = 0.0


@dataclass(frozen=True)
class GachaEntry:
    item_type: str
    item_id: int
    quantity: int
    weight: int


def clamp_probability(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def normalize_distribution(distribution: Sequence[float]) -> list[float]:
    values = [max(0.0, float(value)) for value in distribution]
    total = sum(values)
    if total <= 0:
        raise ValueError("distribution must contain at least one positive weight")
    return [value / total for value in values]


def apply_rare_bonus(
    distribution: Sequence[float],
    rare_bonus: float,
    cap: float = 0.8,
) -> list[float]:
    """Move a share of 1-3 star probability to 4-5 stars.

    The 6+ bucket remains unchanged, matching FishingService.
    """
    if len(distribution) < 6:
        raise ValueError("rarity distribution must contain six buckets")

    adjusted = normalize_distribution(distribution)
    boost = min(max(float(rare_bonus), 0.0), max(float(cap), 0.0))
    low_total = sum(adjusted[:3])
    rare_total = sum(adjusted[3:5])
    if boost == 0 or low_total <= 0 or rare_total <= 0:
        return adjusted

    transfer = low_total * boost
    for index in range(3):
        adjusted[index] -= transfer * adjusted[index] / low_total
    for index in range(3, 5):
        adjusted[index] += transfer * adjusted[index] / rare_total
    return normalize_distribution(adjusted)


def quality_bonus_chance(quality_modifier: float, cap: float = 0.35) -> float:
    """Return the chance that a catch receives the 2x quality sale value."""
    modifier = max(float(quality_modifier), 0.0)
    probability_cap = clamp_probability(cap)
    if modifier <= 1.0 or probability_cap == 0:
        return 0.0
    return min(math.log2(modifier) * probability_cap / 2.0, probability_cap)


def weighted_fish_value(
    base_values: Iterable[float],
    value_weight_exponent: float = 1.0,
) -> float:
    """Expected base value for the runtime's within-rarity weighted draw."""
    values = [max(float(value), 0.0) for value in base_values]
    if not values:
        raise ValueError("base_values cannot be empty")

    exponent = max(float(value_weight_exponent), 0.0)
    weights = [max(value, 1.0) ** exponent for value in values]
    total_weight = sum(weights)
    return sum(value * weight for value, weight in zip(values, weights)) / total_weight


def weighted_fish_metrics(
    base_values: Iterable[float],
    value_weight_exponent: float = 1.0,
    garbage_threshold: float = 5.0,
) -> tuple[float, float, float]:
    """Return expected value, garbage probability, and garbage contribution."""
    values = [max(float(value), 0.0) for value in base_values]
    if not values:
        raise ValueError("base_values cannot be empty")
    exponent = max(float(value_weight_exponent), 0.0)
    weights = [max(value, 1.0) ** exponent for value in values]
    total_weight = sum(weights)
    expected = sum(value * weight for value, weight in zip(values, weights))
    garbage_weight = sum(
        weight
        for value, weight in zip(values, weights)
        if value < garbage_threshold
    )
    garbage_contribution = sum(
        value * weight
        for value, weight in zip(values, weights)
        if value < garbage_threshold
    )
    return (
        expected / total_weight,
        garbage_weight / total_weight,
        garbage_contribution / total_weight,
    )


def expected_fishing_return(
    distribution: Sequence[float],
    fish_values_by_rarity: Mapping[int, Sequence[float]],
    scenario: FishingScenario = FishingScenario(),
    high_rarity_weights: Mapping[int, float] | None = None,
    value_weight_exponent: float = 1.0,
) -> dict[str, float]:
    """Calculate expected gross and net coin return for one fishing command."""
    adjusted = apply_rare_bonus(distribution, scenario.rare_bonus)
    rarity_metrics: dict[int, tuple[float, float, float]] = {}
    for rarity in range(1, 6):
        values = fish_values_by_rarity.get(rarity, ())
        if values:
            rarity_metrics[rarity] = weighted_fish_metrics(
                values, value_weight_exponent
            )

    high_rarities = sorted(
        rarity for rarity, values in fish_values_by_rarity.items()
        if rarity >= 6 and values
    )
    if high_rarities:
        if high_rarity_weights is None:
            high_weights = {rarity: 1.0 for rarity in high_rarities}
        else:
            high_weights = {
                rarity: max(float(high_rarity_weights.get(rarity, 0.0)), 0.0)
                for rarity in high_rarities
            }
            if sum(high_weights.values()) <= 0:
                raise ValueError("high rarity weights must contain a positive value")
        high_total = sum(high_weights.values())
        rarity_metrics[6] = tuple(
            sum(
                weighted_fish_metrics(
                    fish_values_by_rarity[rarity], value_weight_exponent
                )[metric_index]
                * high_weights[rarity]
                / high_total
                for rarity in high_rarities
            )
            for metric_index in range(3)
        )

    missing = [
        bucket + 1
        for bucket, probability in enumerate(adjusted)
        if probability > 0 and bucket + 1 not in rarity_metrics
    ]
    if missing:
        raise ValueError(f"missing fish values for rarity buckets: {missing}")

    expected_base_value = sum(
        probability * rarity_metrics[index + 1][0]
        for index, probability in enumerate(adjusted)
        if probability > 0
    )
    garbage_probability = sum(
        probability * rarity_metrics[index + 1][1]
        for index, probability in enumerate(adjusted)
        if probability > 0
    )
    garbage_value_contribution = sum(
        probability * rarity_metrics[index + 1][2]
        for index, probability in enumerate(adjusted)
        if probability > 0
    )
    garbage_reduction = clamp_probability(scenario.garbage_reduction)
    expected_base_value += garbage_reduction * (
        garbage_probability * expected_base_value
        - garbage_value_contribution
    )
    quality_chance = quality_bonus_chance(
        scenario.quality_modifier, scenario.quality_bonus_cap
    )
    expected_quality_multiplier = 1.0 + quality_chance
    success_rate = clamp_probability(scenario.success_rate)
    quantity = max(float(scenario.quantity_modifier), 0.0)
    value_modifier = max(float(scenario.value_modifier), 0.0)
    gross = (
        success_rate
        * quantity
        * value_modifier
        * expected_quality_multiplier
        * expected_base_value
    )
    cost = (
        max(float(scenario.fishing_cost), 0.0)
        + max(float(scenario.consumable_cost), 0.0)
    )
    net = gross - cost
    cooldown_seconds = max(float(scenario.cooldown_seconds), 0.0)
    attempts_per_hour = 3600.0 / cooldown_seconds if cooldown_seconds > 0 else math.inf
    return {
        "expected_base_value_on_success": expected_base_value,
        "quality_bonus_chance": quality_chance,
        "garbage_probability": garbage_probability,
        "expected_catches": success_rate * quantity,
        "gross_value": gross,
        "cost": cost,
        "net_value": net,
        "return_ratio": gross / cost if cost > 0 else math.inf,
        "attempts_per_hour": attempts_per_hour,
        "gross_value_per_hour": gross * attempts_per_hour,
        "net_value_per_hour": net * attempts_per_hour,
    }


def expected_gacha_return(
    entries: Sequence[GachaEntry],
    item_values: Mapping[tuple[str, int], float],
    draw_cost: float,
) -> dict[str, float]:
    """Calculate expected catalog value for one weighted gacha draw."""
    total_weight = sum(max(entry.weight, 0) for entry in entries)
    if total_weight <= 0:
        raise ValueError("gacha entries must contain positive weight")

    gross = 0.0
    unresolved_probability = 0.0
    for entry in entries:
        probability = max(entry.weight, 0) / total_weight
        key = (entry.item_type, entry.item_id)
        if entry.item_type == "coins":
            unit_value = 1.0
        elif key in item_values:
            unit_value = max(float(item_values[key]), 0.0)
        else:
            unresolved_probability += probability
            continue
        gross += probability * unit_value * max(entry.quantity, 0)

    cost = max(float(draw_cost), 0.0)
    return {
        "gross_value": gross,
        "cost": cost,
        "net_value": gross - cost,
        "return_ratio": gross / cost if cost > 0 else math.inf,
        "unresolved_probability": unresolved_probability,
    }

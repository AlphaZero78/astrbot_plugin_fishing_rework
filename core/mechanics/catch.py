from __future__ import annotations

import math
import random
from typing import Any, Callable, Sequence


def clamp_probability(value: Any, default: float = 0.0) -> float:
    """Convert a value to a probability in the inclusive range [0, 1]."""
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        numeric_value = float(default)
    return min(max(numeric_value, 0.0), 1.0)


def normalize_distribution(distribution: Sequence[float]) -> list[float]:
    """Normalize non-negative rarity weights into a probability distribution."""
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
    """Move 1-3 star weight to 4-5 stars while preserving the 6+ bucket."""
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


def high_rarity_weights(
    rarities: Sequence[int],
    decay: float = 0.5,
) -> dict[int, float]:
    """Return geometrically decreasing weights for available 6+ rarities."""
    available = sorted({int(rarity) for rarity in rarities if rarity >= 6})
    if not available:
        return {}
    decay_factor = min(max(float(decay), 0.0), 1.0)
    return {
        rarity: decay_factor ** (rarity - 6)
        for rarity in available
    }


def quality_bonus_chance(quality_modifier: float, cap: float = 0.35) -> float:
    """Convert a multiplicative quality bonus to its high-quality probability."""
    modifier = max(float(quality_modifier), 0.0)
    probability_cap = clamp_probability(cap)
    if modifier <= 1.0 or probability_cap == 0:
        return 0.0
    return min(math.log2(modifier) * probability_cap / 2.0, probability_cap)


def expected_catch_count(quantity_modifier: float) -> float:
    """Return the runtime expectation, including the guaranteed first catch."""
    return max(float(quantity_modifier), 1.0)


def roll_catch_count(
    quantity_modifier: float,
    random_value: Callable[[], float] = random.random,
) -> int:
    """Resolve the guaranteed and fractional parts of a quantity multiplier."""
    modifier = expected_catch_count(quantity_modifier)
    catches = max(1, int(modifier))
    fractional = modifier - int(modifier)
    if fractional > 0 and random_value() < fractional:
        catches += 1
    return catches

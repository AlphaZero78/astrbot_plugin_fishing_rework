"""Shared game-mechanic helpers."""

from .bait import bait_cost_per_attempt, consumes_bait_per_attempt
from .catch import (
    apply_rare_bonus,
    high_rarity_weights,
    clamp_probability,
    expected_catch_count,
    normalize_distribution,
    quality_bonus_chance,
    roll_catch_count,
)

__all__ = [
    "apply_rare_bonus",
    "high_rarity_weights",
    "bait_cost_per_attempt",
    "clamp_probability",
    "consumes_bait_per_attempt",
    "expected_catch_count",
    "normalize_distribution",
    "quality_bonus_chance",
    "roll_catch_count",
]

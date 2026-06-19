from __future__ import annotations

from typing import Any


def _read(bait: Any, field: str, default: Any) -> Any:
    try:
        return bait[field]
    except (KeyError, TypeError, IndexError):
        return getattr(bait, field, default)


def consumes_bait_per_attempt(bait: Any) -> bool:
    """Return whether one bait is consumed by each fishing attempt."""
    return bool(_read(bait, "is_consumable", True)) and int(
        _read(bait, "duration_minutes", 0) or 0
    ) <= 0


def bait_cost_per_attempt(bait: Any, cooldown_seconds: float) -> float:
    """Amortize bait cost over the attempts covered by its duration."""
    if not bool(_read(bait, "is_consumable", True)):
        return 0.0
    cost = max(float(_read(bait, "cost", 0) or 0), 0.0)
    duration_seconds = max(
        float(_read(bait, "duration_minutes", 0) or 0) * 60.0,
        0.0,
    )
    cooldown = max(float(cooldown_seconds), 0.0)
    if duration_seconds <= 0 or cooldown <= 0:
        return cost
    covered_attempts = max(duration_seconds / cooldown, 1.0)
    return cost / covered_attempts

from __future__ import annotations

from typing import Any


def fish_stack_unit_value(base_value: int, item: Any) -> float | int:
    """Return one fish's sale value, including persisted and quality bonuses."""
    persisted_value = getattr(item, "unit_value", None)
    normal_value = (
        float(persisted_value)
        if persisted_value is not None
        else float(base_value)
    )
    quality_multiplier = 1 + int(getattr(item, "quality_level", 0) or 0)
    value = normal_value * quality_multiplier
    return int(value) if value.is_integer() else round(value, 2)


def fish_stack_total_value(base_value: int, item: Any) -> int:
    """Return a stack's sale value with deterministic final rounding."""
    quantity = max(int(getattr(item, "quantity", 0) or 0), 0)
    return int(round(fish_stack_unit_value(base_value, item) * quantity))

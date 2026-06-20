from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def format_number(value: Any, max_decimals: int = 4) -> str:
    """Format numeric display values without binary-float noise."""
    if value is None:
        return "-"
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    if not number.is_finite():
        return str(value)
    decimals = max(0, int(max_decimals))
    quantizer = Decimal(1).scaleb(-decimals)
    try:
        rounded = number.quantize(quantizer)
    except InvalidOperation:
        rounded = number
    text = format(rounded, "f").rstrip("0").rstrip(".")
    return text if text and text != "-0" else "0"


def format_percent(value: Any, max_decimals: int = 2) -> str:
    """Format a fractional value as a percentage without trailing noise."""
    try:
        percentage = Decimal(str(value)) * Decimal(100)
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    return format_number(percentage, max_decimals)


def format_coins(value: Any) -> str:
    """Format coin-like values with thousands separators."""
    try:
        return f"{int(Decimal(str(value))):,}"
    except (InvalidOperation, TypeError, ValueError):
        return str(value)

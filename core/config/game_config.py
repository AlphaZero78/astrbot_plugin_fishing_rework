from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


EXCHANGE_DEFAULTS = {
    "account_fee": 100000,
    "capacity": 1000,
    "tax_rate": 0.05,
    "volatility": {
        "dried_fish": 0.08,
        "fish_roe": 0.12,
        "fish_oil": 0.10,
    },
    "event_chance": 0.1,
    "max_change_rate": 0.2,
    "min_price": 1,
    "max_price": 1000000,
    "sentiment_weights": {
        "panic": 0.1,
        "pessimistic": 0.2,
        "neutral": 0.4,
        "optimistic": 0.2,
        "euphoric": 0.1,
    },
    "merge_window_minutes": 30,
    "initial_prices": {
        "dried_fish": 6000,
        "fish_roe": 12000,
        "fish_oil": 10000,
    },
}

POND_UPGRADES = [
    {"from": 480, "to": 999, "cost": 50000},
    {"from": 999, "to": 9999, "cost": 500000},
    {"from": 9999, "to": 99999, "cost": 50000000},
    {"from": 99999, "to": 999999, "cost": 5000000000},
]

SELL_PRICE_BY_RARITY = {
    "1": 100,
    "2": 500,
    "3": 2000,
    "4": 5000,
    "5": 10000,
    "6": 20000,
    "7": 50000,
    "8": 100000,
    "9": 200000,
    "10": 500000,
}

REFINE_MULTIPLIERS = {
    "1": 1.0,
    "2": 1.6,
    "3": 3.0,
    "4": 6.0,
    "5": 12.0,
    "6": 25.0,
    "7": 55.0,
    "8": 125.0,
    "9": 280.0,
    "10": 660.0,
}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def deep_merge(defaults: Mapping[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(defaults))
    for key, value in overrides.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def build_game_config(config: Mapping[str, Any]) -> dict[str, Any]:
    fishing = _mapping(config.get("fishing"))
    steal = _mapping(config.get("steal"))
    electric_fish = _mapping(config.get("electric_fish"))
    game = _mapping(config.get("game"))
    user = _mapping(config.get("user"))
    market = _mapping(config.get("market"))
    tax = _mapping(config.get("tax"))
    sell_prices = _mapping(config.get("sell_prices"))
    exchange = deep_merge(EXCHANGE_DEFAULTS, _mapping(config.get("exchange")))

    rarity_prices = {
        rarity: sell_prices.get(f"by_rarity_{rarity}", default)
        for rarity, default in SELL_PRICE_BY_RARITY.items()
    }

    return {
        "fishing": {
            "cost": config.get("fish_cost", 10),
            "cooldown_seconds": fishing.get("cooldown_seconds", 180),
        },
        "quality_bonus_max_chance": fishing.get("quality_bonus_max_chance", 0.35),
        "rare_bonus_max_chance": fishing.get("rare_bonus_max_chance", 0.30),
        "steal": {
            "cooldown_seconds": steal.get("cooldown_seconds", 14400),
        },
        "electric_fish": {
            "enabled": electric_fish.get("enabled", True),
            "cooldown_seconds": electric_fish.get("cooldown_seconds", 7200),
            "base_success_rate": electric_fish.get("base_success_rate", 0.6),
            "failure_penalty_max_rate": electric_fish.get(
                "failure_penalty_max_rate", 0.5
            ),
        },
        "wipe_bomb": {
            "max_attempts_per_day": game.get("wipe_bomb_attempts", 3),
        },
        "wheel_of_fate_daily_limit": game.get("wheel_of_fate_daily_limit", 3),
        "daily_reset_hour": game.get("daily_reset_hour", 0),
        "user": {
            "initial_coins": user.get("initial_coins", 200),
        },
        "market": {
            "listing_tax_rate": market.get("listing_tax_rate", 0.05),
        },
        "tax": {
            "is_tax": tax.get("is_tax", True),
            "threshold": tax.get("threshold", 1000000),
            "step_coins": tax.get("step_coins", 100000),
            "step_rate": tax.get("step_rate", 0.01),
            "min_rate": tax.get("min_rate", 0.001),
            "max_rate": tax.get("max_rate", 0.2),
            "transfer_tax_rate": tax.get("transfer_tax_rate", 0.05),
        },
        "pond_upgrades": deepcopy(POND_UPGRADES),
        "sell_prices": {
            "rod": deepcopy(rarity_prices),
            "accessory": deepcopy(rarity_prices),
            "refine_multiplier": deepcopy(REFINE_MULTIPLIERS),
        },
        "exchange": exchange,
    }

from astrbot_plugin_fishing.core.config.game_config import (
    DEFAULT_RARE_BONUS_CAP,
    EXCHANGE_DEFAULTS,
    build_game_config,
)


def test_build_game_config_uses_central_defaults():
    config = build_game_config({})

    assert config["fishing"]["cooldown_seconds"] == 180
    assert config["quality_bonus_max_chance"] == 0.35
    assert config["rare_bonus_max_chance"] == DEFAULT_RARE_BONUS_CAP
    assert config["tax"]["threshold"] == 1_000_000
    assert config["sell_prices"]["rod"]["6"] == 20_000
    assert config["exchange"] == EXCHANGE_DEFAULTS


def test_build_game_config_deep_merges_nested_exchange_values():
    config = build_game_config(
        {
            "exchange": {
                "capacity": 2500,
                "volatility": {"fish_oil": 0.25},
            }
        }
    )

    assert config["exchange"]["capacity"] == 2500
    assert config["exchange"]["volatility"]["fish_oil"] == 0.25
    assert config["exchange"]["volatility"]["dried_fish"] == 0.08
    assert config["exchange"]["initial_prices"]["fish_roe"] == 12_000


def test_build_game_config_applies_runtime_overrides():
    config = build_game_config(
        {
            "fishing": {
                "cooldown_seconds": 30,
                "quality_bonus_max_chance": 0.2,
                "rare_bonus_max_chance": 0.3,
            },
            "tax": {
                "is_tax": False,
                "transfer_tax_rate": 0.08,
            },
            "sell_prices": {
                "by_rarity_1": 123,
                "by_rarity_10": 999999,
            },
        }
    )

    assert config["fishing"]["cooldown_seconds"] == 30
    assert config["quality_bonus_max_chance"] == 0.2
    assert config["rare_bonus_max_chance"] == 0.3
    assert config["tax"]["is_tax"] is False
    assert config["tax"]["transfer_tax_rate"] == 0.08
    assert config["sell_prices"]["rod"]["1"] == 123
    assert config["sell_prices"]["accessory"]["10"] == 999999

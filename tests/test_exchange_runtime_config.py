from astrbot_plugin_fishing.core.config import build_game_config
from astrbot_plugin_fishing.core.services.exchange_price_service import (
    ExchangePriceService,
)


class _ExchangeRepo:
    def get_prices_for_date(self, _date):
        return []


def test_exchange_market_state_and_prices_hot_apply():
    initial = build_game_config({})
    service = ExchangePriceService(_ExchangeRepo(), initial)

    first = service.get_market_status()
    assert first["prices"]["dried_fish"] == 6000
    assert first["market_sentiment"] == "neutral"

    updated = build_game_config(
        {
            "exchange": {
                "update_timing": "8:30, 20:15",
                "initial_prices": {
                    "dried_fish": 6500,
                    "fish_roe": 12500,
                    "fish_oil": 10500,
                },
                "market_sentiment": "optimistic",
                "price_trend": "rising",
                "supply_demand": "供不应求",
            }
        }
    )
    service.apply_config(updated)
    second = service.get_market_status()

    assert second["prices"]["dried_fish"] == 6500
    assert second["market_sentiment"] == "optimistic"
    assert second["price_trend"] == "rising"
    assert second["supply_demand"] == "供不应求"
    assert [value.strftime("%H:%M") for value in service.get_update_schedule()] == [
        "08:30",
        "20:15",
    ]

from __future__ import annotations

import asyncio
import json

from astrbot_plugin_fishing.core.config import build_game_config
from astrbot_plugin_fishing.core.services.item_template_service import (
    ItemTemplateService,
)
from astrbot_plugin_fishing.core.services.runtime_config_service import (
    RuntimeConfigService,
)
from astrbot_plugin_fishing.manager.server import create_app


class _Config(dict):
    def __init__(self, value):
        super().__init__(value)
        self.saved = 0

    def save_config(self):
        self.saved += 1


class _ItemRepo:
    def __init__(self):
        self.updated = None

    def update_item_template(self, item_id, data):
        self.updated = (item_id, data)


class _ExchangeService:
    def __init__(self):
        self.reset_calls = 0

    def reset_prices_to_initial(self):
        self.reset_calls += 1
        return {"success": True}


def test_admin_routes_persist_settings_and_item_effects(tmp_path):
    async def scenario():
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(
            json.dumps(
                {
                    "webui": {
                        "description": "hidden",
                        "type": "object",
                        "items": {
                            "port": {"type": "int", "default": 7777},
                        },
                    },
                    "fishing": {
                        "description": "fishing",
                        "type": "object",
                        "items": {
                            "cooldown_seconds": {
                                "type": "int",
                                "default": 180,
                                "min": 1,
                            },
                        },
                    },
                    "exchange": {
                        "description": "exchange",
                        "type": "object",
                        "items": {
                            "initial_prices": {
                                "type": "object",
                                "items": {
                                    "dried_fish": {
                                        "type": "int",
                                        "default": 6000,
                                        "min": 1,
                                    },
                                    "fish_roe": {
                                        "type": "int",
                                        "default": 12000,
                                        "min": 1,
                                    },
                                    "fish_oil": {
                                        "type": "int",
                                        "default": 10000,
                                        "min": 1,
                                    },
                                },
                            },
                            "market_sentiment": {
                                "type": "string",
                                "default": "neutral",
                            },
                            "price_trend": {
                                "type": "string",
                                "default": "stable",
                            },
                            "supply_demand": {
                                "type": "string",
                                "default": "平衡",
                            },
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        raw_config = _Config(
            {
                "webui": {"port": 7777},
                "fishing": {"cooldown_seconds": 180},
                "exchange": {
                    "initial_prices": {
                        "dried_fish": 6000,
                        "fish_roe": 12000,
                        "fish_oil": 10000,
                    },
                    "market_sentiment": "neutral",
                    "price_trend": "stable",
                    "supply_demand": "平衡",
                },
            }
        )
        game_config = build_game_config(raw_config)
        runtime_service = RuntimeConfigService(
            raw_config, game_config, schema_path
        )
        item_repo = _ItemRepo()
        item_service = ItemTemplateService(item_repo, None)
        exchange_service = _ExchangeService()
        app = create_app(
            "route-test-secret",
            {
                "runtime_config_service": runtime_service,
                "item_template_service": item_service,
                "exchange_service": exchange_service,
            },
        )
        assert app.jinja_env.filters["number"](1.10002432) == "1.1"
        assert app.jinja_env.filters["percent"](0.02500608) == "2.5"
        assert app.jinja_env.get_template("exchange.html") is not None
        app.config["TESTING"] = True

        client = app.test_client()
        login_response = await client.post(
            "/admin/login",
            form={"secret_key": "route-test-secret"},
        )
        assert login_response.status_code == 302

        settings_response = await client.post(
            "/admin/settings",
            form={"fishing.cooldown_seconds": "240"},
        )
        assert settings_response.status_code == 302
        assert raw_config["fishing"]["cooldown_seconds"] == 240
        assert game_config["fishing"]["cooldown_seconds"] == 240
        assert raw_config.saved == 1

        exchange_response = await client.post(
            "/admin/exchange/settings",
            form={
                "exchange.initial_prices.dried_fish": "6500",
                "exchange.initial_prices.fish_roe": "12500",
                "exchange.initial_prices.fish_oil": "10500",
                "exchange.market_sentiment": "optimistic",
                "exchange.price_trend": "rising",
                "exchange.supply_demand": "供不应求",
                "reset_current_prices": "on",
            },
        )
        assert exchange_response.status_code == 302
        assert raw_config["exchange"]["initial_prices"]["dried_fish"] == 6500
        assert game_config["exchange"]["market_sentiment"] == "optimistic"
        assert game_config["exchange"]["price_trend"] == "rising"
        assert game_config["exchange"]["supply_demand"] == "供不应求"
        assert exchange_service.reset_calls == 1

        item_response = await client.post(
            "/admin/items/edit/15",
            form={
                "name": "时运沙漏",
                "description": "准确预测下一次擦弹倍率",
                "rarity": "5",
                "cost": "10000",
                "is_consumable": "on",
                "effect_type": " FORECAST_WIPE_BOMB ",
                "effect_payload": '{ "mode": "accurate" }',
            },
        )
        assert item_response.status_code == 302
        assert item_repo.updated is not None
        item_id, saved = item_repo.updated
        assert item_id == 15
        assert saved["effect_type"] == "FORECAST_WIPE_BOMB"
        assert saved["effect_payload"] == '{"mode":"accurate"}'
        assert saved["is_consumable"] is True

    asyncio.run(scenario())

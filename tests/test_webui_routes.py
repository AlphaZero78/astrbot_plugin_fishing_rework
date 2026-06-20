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
                }
            ),
            encoding="utf-8",
        )
        raw_config = _Config(
            {
                "webui": {"port": 7777},
                "fishing": {"cooldown_seconds": 180},
            }
        )
        game_config = build_game_config(raw_config)
        runtime_service = RuntimeConfigService(
            raw_config, game_config, schema_path
        )
        item_repo = _ItemRepo()
        item_service = ItemTemplateService(item_repo, None)
        app = create_app(
            "route-test-secret",
            {
                "runtime_config_service": runtime_service,
                "item_template_service": item_service,
            },
        )
        assert app.jinja_env.filters["number"](1.10002432) == "1.1"
        assert app.jinja_env.filters["percent"](0.02500608) == "2.5"
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

from __future__ import annotations

import json

import pytest

from astrbot_plugin_fishing.core.config import build_game_config
from astrbot_plugin_fishing.core.services.runtime_config_service import (
    RuntimeConfigService,
)


class _Config(dict):
    def __init__(self, value):
        super().__init__(value)
        self.saved = 0

    def save_config(self):
        self.saved += 1


def _schema(tmp_path):
    path = tmp_path / "schema.json"
    path.write_text(
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
                        "rare_bonus_max_chance": {
                            "type": "float",
                            "default": 0.3,
                            "min": 0,
                            "max": 1,
                        },
                    },
                },
                "tax": {
                    "description": "tax",
                    "type": "object",
                    "items": {
                        "is_tax": {"type": "bool", "default": True},
                    },
                },
                "storage": {
                    "description": "storage",
                    "type": "object",
                    "items": {
                        "shared_db_path": {"type": "string", "default": ""},
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_settings_hide_webui_and_hot_apply_values(tmp_path):
    raw = _Config(
        {
            "webui": {"port": 7777},
            "fishing": {
                "cooldown_seconds": 180,
                "rare_bonus_max_chance": 0.3,
            },
            "tax": {"is_tax": True},
            "storage": {"shared_db_path": ""},
        }
    )
    game = build_game_config(raw)
    applied = []
    service = RuntimeConfigService(raw, game, _schema(tmp_path), applied.append)

    sections = service.get_sections()
    assert "webui" not in {section["key"] for section in sections}

    result = service.update(
        {
            "fishing.cooldown_seconds": "240",
            "fishing.rare_bonus_max_chance": "0.2",
            "tax.is_tax": "false",
        }
    )

    assert raw["fishing"]["cooldown_seconds"] == 240
    assert game["fishing"]["cooldown_seconds"] == 240
    assert game["rare_bonus_max_chance"] == pytest.approx(0.2)
    assert game["tax"]["is_tax"] is False
    assert raw.saved == 1
    assert applied[-1] is game
    assert result["restart_required"] is False


def test_storage_change_requires_restart(tmp_path):
    raw = _Config({"storage": {"shared_db_path": ""}})
    game = build_game_config(raw)
    service = RuntimeConfigService(raw, game, _schema(tmp_path))

    result = service.update({"storage.shared_db_path": "D:/shared/fish.db"})

    assert result["restart_required"] is True


def test_invalid_value_rolls_back_without_saving(tmp_path):
    raw = _Config(
        {
            "fishing": {
                "cooldown_seconds": 180,
                "rare_bonus_max_chance": 0.3,
            }
        }
    )
    game = build_game_config(raw)
    service = RuntimeConfigService(raw, game, _schema(tmp_path))

    with pytest.raises(ValueError):
        service.update({"fishing.rare_bonus_max_chance": "2"})

    assert raw["fishing"]["rare_bonus_max_chance"] == pytest.approx(0.3)
    assert raw.saved == 0

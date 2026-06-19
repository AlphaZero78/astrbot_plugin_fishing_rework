from __future__ import annotations

from pathlib import Path

import pytest

from astrbot_plugin_fishing.core.services.item_template_service import (
    ItemTemplateService,
)


class _ItemRepo:
    def __init__(self):
        self.added = None
        self.updated = None

    def add_item_template(self, data):
        self.added = data

    def update_item_template(self, item_id, data):
        self.updated = (item_id, data)


def test_item_effect_payload_is_validated_and_normalized():
    repo = _ItemRepo()
    service = ItemTemplateService(repo, None)

    service.update_item_template(
        15,
        {
            "effect_type": " FORECAST_WIPE_BOMB ",
            "effect_payload": '{ "mode": "accurate" }',
        },
    )

    assert repo.updated == (
        15,
        {
            "effect_type": "FORECAST_WIPE_BOMB",
            "effect_payload": '{"mode":"accurate"}',
        },
    )


def test_item_effect_payload_rejects_non_object_json():
    service = ItemTemplateService(_ItemRepo(), None)
    with pytest.raises(ValueError, match="JSON 对象"):
        service.add_item_template(
            {"effect_type": "ADD_COINS", "effect_payload": "[1000]"}
        )


def test_item_webui_exposes_real_effect_fields():
    template = (
        Path(__file__).resolve().parents[1]
        / "manager"
        / "templates"
        / "items.html"
    ).read_text(encoding="utf-8")
    assert 'name="effect_type"' in template
    assert 'name="effect_payload"' in template

from __future__ import annotations

from types import SimpleNamespace

import pytest

from astrbot_plugin_fishing.core.domain.models import GachaPool, GachaPoolItem
from astrbot_plugin_fishing.core.services.gacha_service import GachaService


class _GachaRepo:
    def __init__(self, pool):
        self.pool = pool

    def get_pool_by_id(self, pool_id):
        return self.pool if pool_id == self.pool.gacha_pool_id else None


class _TemplateRepo:
    def get_rod_by_id(self, item_id):
        return SimpleNamespace(name=f"rod-{item_id}", rarity=item_id)


def test_pool_details_reports_actual_probability_without_extra_one():
    pool = GachaPool(
        gacha_pool_id=1,
        name="test",
        items=[
            GachaPoolItem(1, 1, "rod", 1, 1),
            GachaPoolItem(2, 1, "rod", 2, 3),
        ],
    )
    service = GachaService(
        _GachaRepo(pool),
        None,
        None,
        _TemplateRepo(),
        None,
        None,
    )

    result = service.get_pool_details(1)

    assert result["success"] is True
    assert [row["probability"] for row in result["probabilities"]] == pytest.approx(
        [0.25, 0.75]
    )

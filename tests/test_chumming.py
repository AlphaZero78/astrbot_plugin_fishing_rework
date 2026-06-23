from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from astrbot_plugin_fishing.core.domain.models import Bait, User
from astrbot_plugin_fishing.core.services import fishing_service as module
from astrbot_plugin_fishing.core.services.fishing_service import FishingService


class _UserRepo:
    def __init__(self, user):
        self.user = user

    def get_by_id(self, user_id):
        return self.user if self.user.user_id == user_id else None


class _InventoryRepo:
    def __init__(self, inventory):
        self.inventory = inventory

    def get_user_bait_inventory(self, user_id):
        return dict(self.inventory)

    def update_bait_quantity(self, user_id, bait_id, delta):
        self.inventory[bait_id] = self.inventory.get(bait_id, 0) + delta


class _BuffRepo:
    def __init__(self):
        self.buff = None

    def get_active_by_user_and_type(self, user_id, buff_type):
        return self.buff

    def add(self, buff):
        buff.id = 1
        self.buff = buff

    def update(self, buff):
        self.buff = buff


def _bait(bait_id=14, name="实验饵"):
    return Bait(
        bait_id=bait_id,
        name=name,
        rarity=6,
        success_rate_modifier=0.25,
        rare_chance_modifier=0.20,
        garbage_reduction_modifier=0.90,
        value_modifier=1.30,
        quantity_modifier=1.05,
    )


def _service():
    user = User(
        user_id="u1",
        nickname="tester",
        coins=0,
        created_at=datetime(2026, 6, 23),
    )
    inventory_repo = _InventoryRepo({14: 100, 13: 10})
    buff_repo = _BuffRepo()
    baits = {14: _bait(), 13: _bait(13, "巨物诱饵")}
    service = FishingService(
        user_repo=_UserRepo(user),
        inventory_repo=inventory_repo,
        item_template_repo=SimpleNamespace(
            get_bait_by_id=lambda bait_id: baits.get(bait_id)
        ),
        log_repo=SimpleNamespace(),
        buff_repo=buff_repo,
        fishing_zone_service=None,
        config={},
    )
    return service, inventory_repo, buff_repo


def test_chumming_consumes_bait_and_uses_ten_percent_effect(monkeypatch):
    now = datetime(2026, 6, 23, 20, 0, 0)
    monkeypatch.setattr(module, "get_now", lambda: now)
    service, inventory, buffs = _service()

    result = service.chum_bait("u1", 14, 60)

    assert result["success"] is True
    assert inventory.inventory[14] == 40
    assert result["duration_seconds"] == 60
    assert result["effects"]["success_rate_modifier"] == pytest.approx(0.025)
    assert result["effects"]["rare_chance_modifier"] == pytest.approx(0.02)
    assert result["effects"]["garbage_reduction_modifier"] == pytest.approx(
        0.09
    )
    assert result["effects"]["value_modifier"] == pytest.approx(1.03)
    assert result["effects"]["quantity_modifier"] == pytest.approx(1.005)
    assert buffs.buff.expires_at == now + timedelta(seconds=60)


def test_same_bait_extends_duration_and_different_bait_replaces(monkeypatch):
    now = datetime(2026, 6, 23, 20, 0, 0)
    monkeypatch.setattr(module, "get_now", lambda: now)
    service, _, buffs = _service()

    service.chum_bait("u1", 14, 30)
    extended = service.chum_bait("u1", 14, 20)
    assert extended["duration_seconds"] == 50

    replaced = service.chum_bait("u1", 13, 10)
    assert replaced["duration_seconds"] == 10
    assert buffs.buff.expires_at == now + timedelta(seconds=10)


def test_chumming_rejects_insufficient_inventory():
    service, inventory, buffs = _service()

    result = service.chum_bait("u1", 14, 101)

    assert result["success"] is False
    assert inventory.inventory[14] == 100
    assert buffs.buff is None

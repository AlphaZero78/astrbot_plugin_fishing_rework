from __future__ import annotations

import json
import sys
import types
from datetime import datetime


class _DummyLogger:
    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass


if "astrbot.api" not in sys.modules:
    astrbot_module = types.ModuleType("astrbot")
    api_module = types.ModuleType("astrbot.api")
    api_module.logger = _DummyLogger()
    astrbot_module.api = api_module
    sys.modules["astrbot"] = astrbot_module
    sys.modules["astrbot.api"] = api_module

from astrbot_plugin_fishing.core.domain.models import User
from astrbot_plugin_fishing.core.services import game_mechanics_service as mechanics_module
from astrbot_plugin_fishing.core.services.game_mechanics_service import GameMechanicsService


class FakeUserRepo:
    def __init__(self, user: User):
        self.user = user

    def get_by_id(self, user_id: str):
        return self.user if self.user.user_id == user_id else None

    def update(self, user: User):
        self.user = user


class FakeLogRepo:
    def __init__(self):
        self.records = []

    def add_wipe_bomb_log(self, record):
        self.records.append(record)


class FakeBuffRepo:
    def get_active_by_user_and_type(self, user_id: str, buff_type: str):
        return None


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        return None


def build_service(user: User) -> GameMechanicsService:
    service = GameMechanicsService(
        user_repo=FakeUserRepo(user),
        log_repo=FakeLogRepo(),
        inventory_repo=object(),
        item_template_repo=object(),
        buff_repo=FakeBuffRepo(),
        config={"wipe_bomb": {"max_attempts_per_day": 3}},
    )
    service.thread_pool.shutdown(wait=False, cancel_futures=True)
    service.thread_pool = ImmediateExecutor()
    service._check_server_suppression = lambda: False
    return service


def build_user() -> User:
    return User(
        user_id="forecast-user",
        nickname="tester",
        coins=10_000,
        created_at=datetime.now(),
    )


def test_hourglass_always_stores_accurate_forecast(monkeypatch):
    user = build_user()
    service = build_service(user)
    monkeypatch.setattr(mechanics_module, "weighted_random_choice", lambda ranges: (2.0, 3.0, 1))
    monkeypatch.setattr(mechanics_module.random, "uniform", lambda low, high: 2.5)

    result = service.forecast_wipe_bomb(user.user_id)

    assert result["success"] is True
    forecast = json.loads(user.wipe_bomb_forecast)
    assert forecast == {
        "mode": "accurate",
        "tier": "shokichi",
        "multiplier": 2.5,
    }


def test_next_wipe_bomb_uses_and_clears_forecast(monkeypatch):
    user = build_user()
    user.wipe_bomb_forecast = json.dumps(
        {"mode": "accurate", "tier": "kichi", "multiplier": 4.0}
    )
    service = build_service(user)

    def unexpected_random_choice(ranges):
        raise AssertionError("accurate forecast should bypass random selection")

    monkeypatch.setattr(mechanics_module, "weighted_random_choice", unexpected_random_choice)

    result = service.perform_wipe_bomb(user.user_id, 1_000)

    assert result["success"] is True
    assert result["multiplier"] == 4.0
    assert result["reward"] == 4_000
    assert user.coins == 13_000
    assert user.wipe_bomb_forecast is None

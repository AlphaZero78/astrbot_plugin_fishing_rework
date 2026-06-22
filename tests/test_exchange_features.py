import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from astrbot_plugin_fishing.core.config import build_game_config
from astrbot_plugin_fishing.core.domain.models import User, UserCommodity
from astrbot_plugin_fishing.core.services.exchange_price_service import (
    ExchangePriceService,
)
from astrbot_plugin_fishing.core.services.exchange_service import ExchangeService
from astrbot_plugin_fishing.handlers.exchange_handlers import ExchangeHandlers


class _UserRepo:
    def __init__(self, user):
        self.user = user
        self.updates = 0

    def get_by_id(self, _user_id):
        return self.user

    def update(self, user):
        self.user = user
        self.updates += 1


class _PriceRepo:
    def get_prices_for_date(self, _date):
        return []


class _Event:
    def plain_result(self, message):
        return message


class _HandlerExchangeService:
    commodities = {
        "dried_fish": {"name": "鱼干"},
        "fish_roe": {"name": "鱼卵"},
        "fish_oil": {"name": "鱼油"},
    }

    def __init__(self, items):
        self.items = items
        self.upgraded = False

    def check_exchange_account(self, _user_id):
        return {"success": True}

    def get_market_status(self):
        return {
            "success": True,
            "prices": {
                "dried_fish": 120,
                "fish_roe": 240,
                "fish_oil": 180,
            },
            "commodities": self.commodities,
        }

    def get_price_history(self, days=7):
        assert days == 7
        return {
            "success": True,
            "history": {
                "dried_fish": [100, 104, 100, 105],
                "fish_roe": [260, 250, 245, 240],
                "fish_oil": [170, 175, 172, 180],
            },
        }

    def get_user_commodities(self, _user_id):
        return self.items

    def get_capacity_status(self, _user_id):
        return {
            "success": True,
            "current_quantity": sum(item.quantity for item in self.items),
            "capacity": 1000,
            "next_upgrade": {"to": 2000, "cost": 200000},
        }

    def upgrade_capacity(self, _user_id):
        self.upgraded = True
        return {
            "success": True,
            "old_capacity": 1000,
            "new_capacity": 2000,
            "cost": 200000,
        }

    def manual_update_prices(self):
        return {
            "success": True,
            "prices": {
                "dried_fish": 121,
                "fish_roe": 238,
                "fish_oil": 182,
            },
        }

    def reset_prices_to_initial(self):
        return {"success": True}


async def _collect(generator):
    return [value async for value in generator]


def test_exchange_capacity_upgrade_uses_personal_capacity():
    user = User(
        user_id="u1",
        created_at=datetime.now(),
        nickname="tester",
        coins=500000,
        exchange_account_status=True,
        exchange_capacity=1000,
    )
    user_repo = _UserRepo(user)
    service = ExchangeService.__new__(ExchangeService)
    service.user_repo = user_repo
    service.inventory_service = SimpleNamespace(
        _get_user_total_commodity_quantity=lambda _user_id: 600
    )
    service.config = build_game_config({})

    status = service.get_capacity_status("u1")
    assert status["capacity"] == 1000
    assert status["current_quantity"] == 600
    assert status["next_upgrade"]["to"] == 2000

    result = service.upgrade_capacity("u1")
    assert result["success"] is True
    assert result["new_capacity"] == 2000
    assert user_repo.user.exchange_capacity == 2000
    assert user_repo.user.coins == 300000
    assert user_repo.updates == 1


def test_exchange_metrics_and_portfolio_expiry_handling():
    metrics = ExchangeHandlers._price_metrics(
        [100, 105, 110, 108, 115]
    )
    assert metrics["change_rate"] == pytest.approx(15.0)
    assert metrics["trend"] == "rising"
    assert metrics["volatility"] > 0

    now = datetime.now()
    items = [
        UserCommodity(
            instance_id=1,
            user_id="u1",
            commodity_id="dried_fish",
            quantity=10,
            purchase_price=100,
            purchased_at=now - timedelta(days=1),
            expires_at=now + timedelta(hours=12),
        ),
        UserCommodity(
            instance_id=2,
            user_id="u1",
            commodity_id="fish_oil",
            quantity=5,
            purchase_price=200,
            purchased_at=now - timedelta(days=3),
            expires_at=now - timedelta(minutes=1),
        ),
    ]
    snapshot = ExchangeHandlers._portfolio_snapshot(
        items,
        {"dried_fish": 120, "fish_oil": 250},
    )
    assert snapshot["total_cost"] == 2000
    assert snapshot["total_value"] == 1200
    assert snapshot["profit_loss"] == -800
    assert snapshot["expiring_quantity"] == 10
    assert snapshot["expired_quantity"] == 5


def test_price_calculation_uses_per_commodity_volatility(monkeypatch):
    config = build_game_config(
        {
            "exchange": {
                "max_change_rate": 1.0,
                "volatility": {
                    "dried_fish": 0.02,
                    "fish_roe": 0.30,
                    "fish_oil": 0.10,
                },
            }
        }
    )
    service = ExchangePriceService(_PriceRepo(), config)
    monkeypatch.setattr(
        "astrbot_plugin_fishing.core.services.exchange_price_service.random.uniform",
        lambda _low, _high: 1.0,
    )

    assert service._calculate_new_price("dried_fish", 10000) == 10200
    assert service._calculate_new_price("fish_roe", 10000) == 13000

    service.apply_config(
        build_game_config(
            {
                "exchange": {
                    "min_price": 9500,
                    "max_price": 10100,
                    "max_change_rate": 1.0,
                    "volatility": {"dried_fish": 0.5},
                }
            }
        )
    )
    assert service._calculate_new_price("dried_fish", 10000) == 10100


def test_exchange_command_handlers_return_real_analysis():
    now = datetime.now()
    items = [
        UserCommodity(
            instance_id=1,
            user_id="u1",
            commodity_id="dried_fish",
            quantity=10,
            purchase_price=100,
            purchased_at=now,
            expires_at=now + timedelta(days=2),
        )
    ]
    exchange_service = _HandlerExchangeService(items)
    plugin = SimpleNamespace(
        exchange_service=exchange_service,
        user_repo=SimpleNamespace(),
        _get_effective_user_id=lambda _event: "u1",
    )
    handler = ExchangeHandlers(plugin)
    event = _Event()

    profit = asyncio.run(_collect(handler.profit_loss(event)))[0]
    recommendation = asyncio.run(
        _collect(handler.recommendation(event))
    )[0]
    risk = asyncio.run(_collect(handler.risk_assessment(event)))[0]
    capacity = asyncio.run(_collect(handler.capacity_status(event)))[0]
    upgrade = asyncio.run(_collect(handler.upgrade_capacity(event)))[0]
    update = asyncio.run(_collect(handler.admin_update_prices(event)))[0]
    reset = asyncio.run(_collect(handler.admin_reset_prices(event)))[0]

    assert "浮动盈亏：+200" in profit
    assert "鱼干：少量买入" in recommendation
    assert "风险等级" in risk
    assert "下一档：2000" in capacity
    assert "1000 → 2000" in upgrade
    assert "鱼干 121" in update
    assert "重置为当前基础价格" in reset

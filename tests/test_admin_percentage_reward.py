from __future__ import annotations

import asyncio
import sys
import types
from types import SimpleNamespace

permission_module = types.ModuleType("astrbot.core.star.filter.permission")
permission_module.PermissionType = SimpleNamespace(ADMIN="admin")
sys.modules.setdefault(
    "astrbot.core.star.filter.permission",
    permission_module,
)

components_module = types.ModuleType("astrbot.api.message_components")
components_module.At = type("At", (), {})
components_module.Node = type("Node", (), {})
components_module.Plain = type("Plain", (), {})
sys.modules.setdefault("astrbot.api.message_components", components_module)

event_module = sys.modules["astrbot.api.event"]
event_module.filter = SimpleNamespace()

from astrbot_plugin_fishing.handlers.admin_handlers import reward_all_coins


class _UserRepo:
    def __init__(self):
        self.users = {
            "low": SimpleNamespace(coins=9),
            "mid": SimpleNamespace(coins=12_345),
            "high": SimpleNamespace(coins=100_000),
        }
        self.updated = []

    def get_all_user_ids(self):
        return list(self.users)

    def get_by_id(self, user_id):
        return self.users[user_id]

    def update(self, user):
        self.updated.append(user)


class _Event:
    message_str = "/全体奖励金币 2.5%"

    @staticmethod
    def plain_result(message):
        return message


def test_reward_all_coins_percentage_uses_each_balance_and_rounds_down():
    repo = _UserRepo()
    plugin = SimpleNamespace(user_repo=repo)

    async def collect_messages():
        return [
            message async for message in reward_all_coins(plugin, _Event())
        ]

    messages = asyncio.run(collect_messages())

    assert repo.users["low"].coins == 9
    assert repo.users["mid"].coins == 12_653
    assert repo.users["high"].coins == 102_500
    assert len(repo.updated) == 2
    assert "实际发放：2 人" in messages[0]
    assert "发放总额：2,808 金币" in messages[0]
    assert "取整后为 0：1 人" in messages[0]

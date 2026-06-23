import asyncio
from types import SimpleNamespace

from astrbot_plugin_fishing.core.services.sicbo_service import SicboService
from astrbot_plugin_fishing.handlers.red_packet_handlers import (
    cleanup_red_packets,
)


def test_force_settle_all_games_covers_every_active_session(monkeypatch):
    service = SicboService.__new__(SicboService)
    service.games = {
        "group-a": SimpleNamespace(is_active=True),
        "group-b": SimpleNamespace(is_active=True),
        "group-c": SimpleNamespace(is_active=False),
    }
    settled = []

    async def fake_settle(session_id):
        settled.append(session_id)
        return {"success": True, "message": "ok"}

    monkeypatch.setattr(service, "force_settle_game", fake_settle)

    result = asyncio.run(service.force_settle_all_games())

    assert result["success"] is True
    assert result["settled_count"] == 2
    assert settled == ["group-a", "group-b"]


def test_force_settle_all_games_reports_empty_global_state():
    service = SicboService.__new__(SicboService)
    service.games = {
        "group-a": SimpleNamespace(is_active=False),
    }

    result = asyncio.run(service.force_settle_all_games())

    assert result["success"] is False
    assert result["settled_count"] == 0
    assert "所有会话" in result["message"]


def test_admin_red_packet_cleanup_uses_global_scope():
    calls = []

    class _Event:
        def is_admin(self):
            return True

        def plain_result(self, message):
            return message

    service = SimpleNamespace(
        clean_all_red_packets=lambda: calls.append("all")
        or {"message": "done"},
        clean_group_red_packets=lambda group_id: calls.append(group_id),
    )
    plugin = SimpleNamespace(red_packet_service=service)

    async def collect():
        return [
            result
            async for result in cleanup_red_packets(plugin, _Event())
        ]

    results = asyncio.run(collect())

    assert results == ["done"]
    assert calls == ["all"]

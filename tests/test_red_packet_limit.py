from datetime import datetime

from astrbot_plugin_fishing.core.domain.models import User
from astrbot_plugin_fishing.core.services.red_packet_service import (
    RedPacketService,
)


class _UserRepo:
    def __init__(self):
        self.user = User(
            user_id="sender",
            nickname="sender",
            coins=100_000_000,
            created_at=datetime(2026, 6, 23),
        )

    def get_by_id(self, user_id):
        return self.user if user_id == self.user.user_id else None

    def update(self, user):
        self.user = user


class _PacketRepo:
    def __init__(self):
        self.packets = []

    def create_red_packet(self, packet):
        self.packets.append(packet)
        return len(self.packets)


def _service():
    packet_repo = _PacketRepo()
    user_repo = _UserRepo()
    return RedPacketService(packet_repo, user_repo), packet_repo, user_repo


def test_normal_packet_total_cannot_exceed_ten_million():
    service, packet_repo, user_repo = _service()

    result = service.send_red_packet(
        "sender", "group", "normal", 1_000_000, count=11
    )

    assert result["success"] is False
    assert "10,000,000" in result["message"]
    assert packet_repo.packets == []
    assert user_repo.user.coins == 100_000_000


def test_lucky_packet_total_cannot_exceed_ten_million():
    service, packet_repo, user_repo = _service()

    result = service.send_red_packet(
        "sender", "group", "lucky", 10_000_001, count=200
    )

    assert result["success"] is False
    assert packet_repo.packets == []
    assert user_repo.user.coins == 100_000_000


def test_packet_at_ten_million_is_allowed():
    service, packet_repo, user_repo = _service()

    result = service.send_red_packet(
        "sender", "group", "password", 1_000_000, count=10, password="ok"
    )

    assert result["success"] is True
    assert len(packet_repo.packets) == 1
    assert packet_repo.packets[0].total_amount == 10_000_000
    assert user_repo.user.coins == 90_000_000

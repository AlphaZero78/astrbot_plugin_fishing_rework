from datetime import datetime, timezone
from types import SimpleNamespace

from astrbot_plugin_fishing.core.domain.models import User
from astrbot_plugin_fishing.core.services.user_service import UserService


class _UserRepo:
    def __init__(self, *users):
        self.users = {user.user_id: user for user in users}
        self.reclassified = []

    def get_by_id(self, user_id):
        return self.users.get(user_id)

    def update(self, user):
        self.users[user.user_id] = user

    def reclassify_latest_income(self, **kwargs):
        self.reclassified.append(kwargs)


class _LogRepo:
    def __init__(self):
        self.records = []

    def add_tax_record(self, record):
        self.records.append(record)


def _service(sender_coins=10_000, tax_enabled=True):
    created_at = datetime(2026, 6, 23, tzinfo=timezone.utc)
    sender = User(
        user_id="sender",
        nickname="sender",
        coins=sender_coins,
        created_at=created_at,
    )
    receiver = User(
        user_id="receiver",
        nickname="receiver",
        coins=0,
        created_at=created_at,
    )
    user_repo = _UserRepo(sender, receiver)
    service = UserService(
        user_repo=user_repo,
        log_repo=_LogRepo(),
        inventory_repo=SimpleNamespace(),
        item_template_repo=SimpleNamespace(),
        gacha_service=SimpleNamespace(),
        config={
            "tax": {
                "is_tax": tax_enabled,
                "transfer_tax_rate": 0.05,
            }
        },
    )
    return service, user_repo


def test_transfer_reserves_outstanding_income_tax():
    service, user_repo = _service()
    service.set_tax_estimate_provider(
        lambda user_id: {
            "success": True,
            "outstanding_tax": 2_000,
        }
    )

    result = service.transfer_coins("sender", "receiver", 8_000)

    assert result["success"] is False
    assert "待缴所得税预留：2,000 金币" in result["message"]
    assert "可转账余额：8,000 金币" in result["message"]
    assert user_repo.users["sender"].coins == 10_000
    assert user_repo.users["receiver"].coins == 0


def test_transfer_allows_spending_only_unreserved_balance():
    service, user_repo = _service()
    service.set_tax_estimate_provider(
        lambda user_id: {
            "success": True,
            "outstanding_tax": 2_000,
        }
    )

    result = service.transfer_coins("sender", "receiver", 7_600)

    assert result["success"] is True
    assert user_repo.users["sender"].coins == 2_020
    assert user_repo.users["receiver"].coins == 7_600


def test_transfer_reserve_is_disabled_when_income_tax_is_disabled():
    service, user_repo = _service(tax_enabled=False)
    service.set_tax_estimate_provider(
        lambda user_id: {
            "success": True,
            "outstanding_tax": 9_000,
        }
    )

    result = service.transfer_coins("sender", "receiver", 8_000)

    assert result["success"] is True
    assert user_repo.users["sender"].coins == 1_600
    assert user_repo.users["receiver"].coins == 8_000

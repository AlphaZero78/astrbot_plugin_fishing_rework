from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from astrbot_plugin_fishing.core.domain.models import User
from astrbot_plugin_fishing.core.services import sicbo_service as sicbo_module
from astrbot_plugin_fishing.core.services.sicbo_service import (
    SicboBet,
    SicboGame,
    SicboService,
)
from astrbot_plugin_fishing.core.utils import get_now


class FakeUserRepo:
    def __init__(self, user: User):
        self.user = user
        self.income_classifications = []

    def get_by_id(self, user_id: str):
        return self.user if self.user.user_id == user_id else None

    def update(self, user: User):
        self.user = user

    def reclassify_latest_income(
        self, user_id, gross_amount, balance_after, taxable_amount, source
    ):
        self.income_classifications.append(
            {
                "user_id": user_id,
                "gross_amount": gross_amount,
                "balance_after": balance_after,
                "taxable_amount": taxable_amount,
                "source": source,
            }
        )
        return True


def test_multiplayer_sicbo_taxes_payout_minus_stake(monkeypatch):
    user = User(
        user_id="sicbo-user",
        nickname="tester",
        coins=9_000,
        created_at=datetime.now(),
    )
    user_repo = FakeUserRepo(user)
    service = SicboService(user_repo, object(), {"sicbo": {}})
    now = get_now()
    service.games["session"] = SicboGame(
        game_id="game-1",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        bets=[
            SicboBet(
                user_id=user.user_id,
                bet_type="大",
                amount=1_000,
                odds=1.0,
            )
        ],
    )
    rolls = iter([4, 4, 5])
    monkeypatch.setattr(
        sicbo_module.random, "randint", lambda low, high: next(rolls)
    )

    result = asyncio.run(service._settle_game("session"))

    assert result["success"] is True
    assert user.coins == 11_000
    assert user_repo.income_classifications[-1] == {
        "user_id": user.user_id,
        "gross_amount": 2_000,
        "balance_after": 11_000,
        "taxable_amount": 1_000,
        "source": "多人骰宝净盈利",
    }

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import time

from astrbot_plugin_fishing.core.services import fishing_service
from astrbot_plugin_fishing.core.services.fishing_service import FishingService


UTC8 = timezone(timedelta(hours=8))


class _Repo:
    db_path = None


def _service() -> FishingService:
    return FishingService(
        user_repo=_Repo(),
        inventory_repo=_Repo(),
        item_template_repo=_Repo(),
        log_repo=_Repo(),
        buff_repo=_Repo(),
        fishing_zone_service=None,
        config={"daily_reset_hour": 12},
    )


def test_next_daily_tax_is_always_a_future_fixed_time(monkeypatch):
    service = _service()
    service.daily_reset_hour = 0

    monkeypatch.setattr(
        fishing_service,
        "get_now",
        lambda: datetime(2026, 6, 22, 10, 27, tzinfo=UTC8),
    )
    assert service._seconds_until_next_daily_tax() == 93 * 60

    monkeypatch.setattr(
        fishing_service,
        "get_now",
        lambda: datetime(2026, 6, 22, 12, 0, tzinfo=UTC8),
    )
    assert service._seconds_until_next_daily_tax() == 24 * 60 * 60

    monkeypatch.setattr(
        fishing_service,
        "get_now",
        lambda: datetime(2026, 6, 22, 12, 27, tzinfo=UTC8),
    )
    assert service._seconds_until_next_daily_tax() == (23 * 60 + 33) * 60


def test_runtime_reset_hour_change_does_not_move_noon_tax():
    service = _service()
    service.reschedule_daily_tax_task(3)

    assert service.daily_reset_hour == 3
    assert service.daily_tax_hour == 12


def test_starting_tax_scheduler_does_not_collect_immediately(monkeypatch):
    service = _service()
    collected = []
    monkeypatch.setattr(
        service,
        "_seconds_until_next_daily_tax",
        lambda: 3600,
    )
    monkeypatch.setattr(
        service,
        "apply_daily_taxes",
        lambda period_end=None: collected.append(True),
    )

    service.start_daily_tax_task()
    time.sleep(0.05)
    service.stop_daily_tax_task()

    assert collected == []


def test_scheduler_collects_once_when_fixed_time_arrives(monkeypatch):
    service = _service()
    collected = []
    monkeypatch.setattr(
        service,
        "_seconds_until_next_daily_tax",
        lambda: 0,
    )
    monkeypatch.setattr(
        service,
        "_acquire_runtime_lock",
        lambda *args: True,
    )
    monkeypatch.setattr(
        service,
        "_release_runtime_lock",
        lambda *args: None,
    )

    def collect_once(period_end=None):
        collected.append(True)
        service.tax_running = False

    monkeypatch.setattr(service, "apply_daily_taxes", collect_once)
    service.tax_running = True
    service._daily_tax_loop()

    assert collected == [True]

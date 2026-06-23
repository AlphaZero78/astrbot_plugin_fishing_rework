from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from astrbot_plugin_fishing.core.repositories.sqlite_log_repo import (
    SqliteLogRepository,
)
from astrbot_plugin_fishing.core.repositories.sqlite_user_repo import (
    SqliteUserRepository,
)
from astrbot_plugin_fishing.core.services.fishing_service import FishingService


UTC8 = timezone(timedelta(hours=8))


def _load_migration(filename):
    path = (
        Path(__file__).resolve().parents[1]
        / "core"
        / "database"
        / "migrations"
        / filename
    )
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _apply_income_migrations(connection):
    _load_migration("049_add_income_ledger.py").up(connection.cursor())
    _load_migration("050_classify_taxable_income.py").up(connection.cursor())


def test_income_trigger_records_gross_and_taxable_credits(tmp_path):
    database = tmp_path / "fish.db"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE users (user_id TEXT PRIMARY KEY, coins INTEGER NOT NULL)"
    )
    connection.execute("INSERT INTO users VALUES ('u1', 10000000)")
    _apply_income_migrations(connection)

    connection.execute("UPDATE users SET coins = 15000000 WHERE user_id = 'u1'")
    connection.execute("UPDATE users SET coins = 2000000 WHERE user_id = 'u1'")
    connection.execute("UPDATE users SET coins = 12000000 WHERE user_id = 'u1'")
    connection.commit()

    rows = connection.execute(
        """
        SELECT amount, taxable_amount
        FROM income_records
        ORDER BY income_id
        """
    ).fetchall()
    assert rows == [(5_000_000, 5_000_000), (10_000_000, 10_000_000)]
    assert sum(row[0] for row in rows) == 15_000_000


def test_transfer_credit_can_be_reclassified_as_non_taxable(tmp_path):
    database = tmp_path / "fish.db"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE users (user_id TEXT PRIMARY KEY, coins INTEGER NOT NULL)"
    )
    connection.execute("INSERT INTO users VALUES ('u1', 10000000)")
    _apply_income_migrations(connection)
    connection.execute("UPDATE users SET coins = 15000000 WHERE user_id = 'u1'")
    connection.commit()
    connection.close()

    repo = SqliteUserRepository(str(database))
    assert repo.reclassify_latest_income(
        "u1",
        gross_amount=5_000_000,
        balance_after=15_000_000,
        taxable_amount=0,
        source="用户转账（免税）",
    )
    with sqlite3.connect(database) as check:
        row = check.execute(
            """
            SELECT amount, taxable_amount, source
            FROM income_records
            """
        ).fetchone()
    assert row == (5_000_000, 0, "用户转账（免税）")


def test_upgrade_exempts_unclassified_legacy_income(tmp_path):
    database = tmp_path / "fish.db"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE users (user_id TEXT PRIMARY KEY, coins INTEGER NOT NULL)"
    )
    connection.execute("INSERT INTO users VALUES ('u1', 10000000)")
    _load_migration("049_add_income_ledger.py").up(connection.cursor())
    connection.execute("UPDATE users SET coins = 15000000 WHERE user_id = 'u1'")
    _load_migration("050_classify_taxable_income.py").up(connection.cursor())
    connection.commit()

    row = connection.execute(
        "SELECT amount, taxable_amount FROM income_records"
    ).fetchone()
    connection.close()
    assert row == (5_000_000, 0)


@pytest.mark.parametrize(
    ("income", "expected_tax"),
    [
        (1_000_000, 0),
        (1_100_000, 100),
        (1_200_000, 1_200),
        (3_000_000, 192_000),
        (4_000_000, 392_000),
    ],
)
def test_progressive_income_tax_uses_marginal_brackets(income, expected_tax):
    tax, taxable, effective_rate = (
        FishingService._calculate_progressive_income_tax(
            income,
            threshold=1_000_000,
            step_coins=100_000,
            step_rate=0.01,
            min_rate=0.001,
            max_rate=0.2,
        )
    )
    assert tax == expected_tax
    assert taxable == max(income - 1_000_000, 0)
    assert effective_rate == pytest.approx(
        expected_tax / income if income else 0
    )


def test_daily_income_tax_records_period_and_deducts_once(tmp_path):
    database = tmp_path / "fish.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            nickname TEXT,
            coins INTEGER,
            premium_currency INTEGER DEFAULT 0,
            total_fishing_count INTEGER DEFAULT 0,
            total_weight_caught REAL DEFAULT 0,
            total_coins_earned INTEGER DEFAULT 0,
            max_coins INTEGER DEFAULT 0,
            consecutive_login_days INTEGER DEFAULT 0,
            fish_pond_capacity INTEGER DEFAULT 50,
            aquarium_capacity INTEGER DEFAULT 50,
            created_at DATETIME,
            equipped_rod_instance_id INTEGER,
            equipped_accessory_instance_id INTEGER,
            current_title_id INTEGER,
            current_bait_id INTEGER,
            bait_start_time DATETIME,
            max_wipe_bomb_multiplier REAL DEFAULT 0,
            min_wipe_bomb_multiplier REAL,
            auto_fishing_enabled INTEGER DEFAULT 0,
            last_fishing_time DATETIME,
            last_wipe_bomb_time DATETIME,
            last_steal_time DATETIME,
            last_electric_fish_time DATETIME,
            last_login_time DATETIME,
            last_stolen_at DATETIME,
            wipe_bomb_forecast TEXT,
            fishing_zone_id INTEGER DEFAULT 1,
            wipe_bomb_attempts_today INTEGER DEFAULT 0,
            last_wipe_bomb_date TEXT,
            in_wheel_of_fate INTEGER DEFAULT 0,
            wof_current_level INTEGER DEFAULT 0,
            wof_current_prize INTEGER DEFAULT 0,
            wof_entry_fee INTEGER DEFAULT 0,
            last_wof_play_time DATETIME,
            wof_last_action_time DATETIME,
            wof_plays_today INTEGER DEFAULT 0,
            last_wof_date TEXT,
            last_sicbo_time DATETIME,
            exchange_account_status INTEGER DEFAULT 0,
            exchange_capacity INTEGER DEFAULT 1000
        );
        CREATE TABLE taxes (
            tax_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            tax_amount INTEGER NOT NULL,
            tax_rate REAL NOT NULL,
            original_amount INTEGER NOT NULL,
            timestamp DATETIME,
            tax_type TEXT NOT NULL,
            balance_after INTEGER NOT NULL
        );
        """
    )
    connection.execute(
        """
        INSERT INTO users (user_id, nickname, coins, created_at)
        VALUES ('u1', 'tester', 5000000, '2026-06-20 00:00:00')
        """
    )
    _apply_income_migrations(connection)
    connection.execute(
        """
        INSERT INTO income_records (
            user_id, amount, taxable_amount, balance_after, source, timestamp
        )
        VALUES ('u1', 1200000, 1200000, 5000000, 'test', ?)
        """,
        ("2026-06-22 10:00:00+08:00",),
    )
    connection.commit()
    connection.close()

    user_repo = SqliteUserRepository(str(database))
    log_repo = SqliteLogRepository(str(database))
    service = FishingService(
        user_repo=user_repo,
        inventory_repo=SimpleNamespace(),
        item_template_repo=SimpleNamespace(),
        log_repo=log_repo,
        buff_repo=SimpleNamespace(),
        fishing_zone_service=None,
        config={
            "daily_reset_hour": 12,
            "tax": {
                "is_tax": True,
                "threshold": 1_000_000,
                "step_coins": 100_000,
                "step_rate": 0.01,
                "min_rate": 0.001,
                "max_rate": 0.2,
            },
        },
    )
    period_end = datetime(2026, 6, 22, 12, 0, tzinfo=UTC8)

    service.apply_daily_taxes(period_end)
    service.apply_daily_taxes(period_end)

    user = user_repo.get_by_id("u1")
    records = log_repo.get_tax_records("u1", limit=10)
    assert user.coins == 4_998_800
    assert len(records) == 1
    assert records[0].tax_amount == 1_200
    assert records[0].original_amount == 1_200_000
    assert "应税盈利 1,200,000 金币" in records[0].tax_type
    assert "应税收入 200,000 金币" in records[0].tax_type


def test_daily_income_tax_ignores_unpaid_amount_without_negative_balance(tmp_path):
    database = tmp_path / "fish.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            nickname TEXT,
            coins INTEGER,
            premium_currency INTEGER DEFAULT 0,
            total_fishing_count INTEGER DEFAULT 0,
            total_weight_caught REAL DEFAULT 0,
            total_coins_earned INTEGER DEFAULT 0,
            max_coins INTEGER DEFAULT 0,
            consecutive_login_days INTEGER DEFAULT 0,
            fish_pond_capacity INTEGER DEFAULT 50,
            aquarium_capacity INTEGER DEFAULT 50,
            created_at DATETIME,
            equipped_rod_instance_id INTEGER,
            equipped_accessory_instance_id INTEGER,
            current_title_id INTEGER,
            current_bait_id INTEGER,
            bait_start_time DATETIME,
            max_wipe_bomb_multiplier REAL DEFAULT 0,
            min_wipe_bomb_multiplier REAL,
            auto_fishing_enabled INTEGER DEFAULT 0,
            last_fishing_time DATETIME,
            last_wipe_bomb_time DATETIME,
            last_steal_time DATETIME,
            last_electric_fish_time DATETIME,
            last_login_time DATETIME,
            last_stolen_at DATETIME,
            wipe_bomb_forecast TEXT,
            fishing_zone_id INTEGER DEFAULT 1,
            wipe_bomb_attempts_today INTEGER DEFAULT 0,
            last_wipe_bomb_date TEXT,
            in_wheel_of_fate INTEGER DEFAULT 0,
            wof_current_level INTEGER DEFAULT 0,
            wof_current_prize INTEGER DEFAULT 0,
            wof_entry_fee INTEGER DEFAULT 0,
            last_wof_play_time DATETIME,
            wof_last_action_time DATETIME,
            wof_plays_today INTEGER DEFAULT 0,
            last_wof_date TEXT,
            last_sicbo_time DATETIME,
            exchange_account_status INTEGER DEFAULT 0,
            exchange_capacity INTEGER DEFAULT 1000
        );
        CREATE TABLE taxes (
            tax_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            tax_amount INTEGER NOT NULL,
            tax_rate REAL NOT NULL,
            original_amount INTEGER NOT NULL,
            timestamp DATETIME,
            tax_type TEXT NOT NULL,
            balance_after INTEGER NOT NULL
        );
        """
    )
    connection.execute(
        """
        INSERT INTO users (user_id, nickname, coins, created_at)
        VALUES ('u1', 'tester', 100, '2026-06-20 00:00:00')
        """
    )
    _apply_income_migrations(connection)
    connection.execute(
        """
        INSERT INTO income_records (
            user_id, amount, taxable_amount, balance_after, source, timestamp
        )
        VALUES ('u1', 1200000, 1200000, 100, 'test', ?)
        """,
        ("2026-06-22 10:00:00+08:00",),
    )
    connection.commit()
    connection.close()

    user_repo = SqliteUserRepository(str(database))
    log_repo = SqliteLogRepository(str(database))
    service = FishingService(
        user_repo=user_repo,
        inventory_repo=SimpleNamespace(),
        item_template_repo=SimpleNamespace(),
        log_repo=log_repo,
        buff_repo=SimpleNamespace(),
        fishing_zone_service=None,
        config={
            "daily_reset_hour": 12,
            "tax": {
                "is_tax": True,
                "threshold": 1_000_000,
                "step_coins": 100_000,
                "step_rate": 0.01,
                "min_rate": 0.001,
                "max_rate": 0.2,
            },
        },
    )
    service.apply_daily_taxes(
        datetime(2026, 6, 22, 12, 0, tzinfo=UTC8)
    )

    user = user_repo.get_by_id("u1")
    record = log_repo.get_tax_records("u1", limit=1)[0]
    assert user.coins == 0
    assert record.tax_amount == 100
    assert "未缴 1,100 金币已忽略" in record.tax_type


def test_daily_income_tax_liquidates_exchange_before_ignoring_remainder(tmp_path):
    database = tmp_path / "fish.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            nickname TEXT,
            coins INTEGER,
            premium_currency INTEGER DEFAULT 0,
            total_fishing_count INTEGER DEFAULT 0,
            total_weight_caught REAL DEFAULT 0,
            total_coins_earned INTEGER DEFAULT 0,
            max_coins INTEGER DEFAULT 0,
            consecutive_login_days INTEGER DEFAULT 0,
            fish_pond_capacity INTEGER DEFAULT 50,
            aquarium_capacity INTEGER DEFAULT 50,
            created_at DATETIME,
            equipped_rod_instance_id INTEGER,
            equipped_accessory_instance_id INTEGER,
            current_title_id INTEGER,
            current_bait_id INTEGER,
            bait_start_time DATETIME,
            max_wipe_bomb_multiplier REAL DEFAULT 0,
            min_wipe_bomb_multiplier REAL,
            auto_fishing_enabled INTEGER DEFAULT 0,
            last_fishing_time DATETIME,
            last_wipe_bomb_time DATETIME,
            last_steal_time DATETIME,
            last_electric_fish_time DATETIME,
            last_login_time DATETIME,
            last_stolen_at DATETIME,
            wipe_bomb_forecast TEXT,
            fishing_zone_id INTEGER DEFAULT 1,
            wipe_bomb_attempts_today INTEGER DEFAULT 0,
            last_wipe_bomb_date TEXT,
            in_wheel_of_fate INTEGER DEFAULT 0,
            wof_current_level INTEGER DEFAULT 0,
            wof_current_prize INTEGER DEFAULT 0,
            wof_entry_fee INTEGER DEFAULT 0,
            last_wof_play_time DATETIME,
            wof_last_action_time DATETIME,
            wof_plays_today INTEGER DEFAULT 0,
            last_wof_date TEXT,
            last_sicbo_time DATETIME,
            exchange_account_status INTEGER DEFAULT 0,
            exchange_capacity INTEGER DEFAULT 1000
        );
        CREATE TABLE taxes (
            tax_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            tax_amount INTEGER NOT NULL,
            tax_rate REAL NOT NULL,
            original_amount INTEGER NOT NULL,
            timestamp DATETIME,
            tax_type TEXT NOT NULL,
            balance_after INTEGER NOT NULL
        );
        """
    )
    connection.execute(
        """
        INSERT INTO users (user_id, nickname, coins, created_at)
        VALUES ('u1', 'tester', 100, '2026-06-20 00:00:00')
        """
    )
    _apply_income_migrations(connection)
    connection.execute(
        """
        INSERT INTO income_records (
            user_id, amount, taxable_amount, balance_after, source, timestamp
        )
        VALUES ('u1', 1200000, 1200000, 100, 'test', ?)
        """,
        ("2026-06-22 10:00:00+08:00",),
    )
    connection.commit()
    connection.close()

    user_repo = SqliteUserRepository(str(database))
    log_repo = SqliteLogRepository(str(database))

    class FakeExchangeService:
        def clear_all_inventory(self, user_id):
            user = user_repo.get_by_id(user_id)
            user.coins += 500
            user_repo.update(user)
            return {"success": True, "net_income": 500}

    service = FishingService(
        user_repo=user_repo,
        inventory_repo=SimpleNamespace(),
        item_template_repo=SimpleNamespace(),
        log_repo=log_repo,
        buff_repo=SimpleNamespace(),
        fishing_zone_service=None,
        config={
            "daily_reset_hour": 12,
            "tax": {
                "is_tax": True,
                "threshold": 1_000_000,
                "step_coins": 100_000,
                "step_rate": 0.01,
                "min_rate": 0.001,
                "max_rate": 0.2,
            },
        },
    )
    notifications = []
    service.register_notifier(
        lambda target, message: notifications.append((target, message))
    )
    service.set_exchange_service(FakeExchangeService())
    service.apply_daily_taxes(
        datetime(2026, 6, 22, 12, 0, tzinfo=UTC8)
    )

    user = user_repo.get_by_id("u1")
    record = log_repo.get_tax_records("u1", limit=1)[0]
    assert user.coins == 0
    assert record.tax_amount == 600
    assert "自动清仓交易所，净收入 500 金币" in record.tax_type
    assert "未缴 600 金币已忽略" in record.tax_type
    assert len(notifications) == 1
    assert notifications[0][0] == "u1"
    assert "已自动清仓交易所持仓" in notifications[0][1]
    assert "实际缴纳：600 金币" in notifications[0][1]
    assert "忽略未缴：600 金币" in notifications[0][1]

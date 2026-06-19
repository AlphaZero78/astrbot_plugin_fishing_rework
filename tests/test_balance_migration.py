from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sqlite3


def _load_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "core"
        / "database"
        / "migrations"
        / "042_rebalance_zones_and_gacha.py"
    )
    spec = importlib.util.spec_from_file_location("balance_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _database():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE fishing_zones (
            id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            daily_rare_fish_quota INTEGER,
            rare_fish_caught_today INTEGER DEFAULT 0,
            configs TEXT,
            is_active INTEGER DEFAULT 1,
            available_from TEXT,
            available_until TEXT,
            required_item_id INTEGER,
            requires_pass INTEGER DEFAULT 0,
            fishing_cost INTEGER DEFAULT 10
        );
        CREATE TABLE gacha_pools (
            gacha_pool_id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            cost_coins INTEGER,
            cost_premium_currency INTEGER DEFAULT 0,
            is_limited_time INTEGER DEFAULT 0,
            open_until TEXT
        );
        CREATE TABLE gacha_pool_items (
            gacha_pool_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            gacha_pool_id INTEGER,
            item_type TEXT,
            item_id INTEGER,
            quantity INTEGER,
            weight INTEGER
        );
        INSERT INTO fishing_zones (
            id, name, description, daily_rare_fish_quota, configs, fishing_cost
        ) VALUES (1, 'old', 'old', 1, '{}', 10);
        INSERT INTO gacha_pools (
            gacha_pool_id, name, description, cost_coins
        ) VALUES
            (4, 'standard', '', 10),
            (5, 'rod', '', 1000),
            (6, 'accessory', '', 1000);
        """
    )
    return connection


def test_balance_migration_sets_zone_and_pool_targets_idempotently():
    migration = _load_migration()
    connection = _database()

    migration.up(connection.cursor())
    migration.up(connection.cursor())

    zones = connection.execute(
        "SELECT id, configs, fishing_cost FROM fishing_zones ORDER BY id"
    ).fetchall()
    assert [row[2] for row in zones] == [16, 89, 1425, 3660]
    assert json.loads(zones[2][1])["rarity_distribution"][-1] == 0.01

    costs = dict(
        connection.execute(
            "SELECT gacha_pool_id, cost_coins FROM gacha_pools"
        ).fetchall()
    )
    assert costs == {4: 13, 5: 1500, 6: 850, 7: 15000}
    assert connection.execute(
        "SELECT COUNT(*) FROM gacha_pool_items WHERE gacha_pool_id = 7"
    ).fetchone()[0] == 14

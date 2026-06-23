from __future__ import annotations

import importlib.util
from pathlib import Path
import sqlite3


def _load_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "core"
        / "database"
        / "migrations"
        / "052_sync_instance_catalog.py"
    )
    spec = importlib.util.spec_from_file_location("catalog_sync", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _database():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE fish (
            fish_id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            description TEXT,
            rarity INTEGER,
            base_value INTEGER,
            min_weight INTEGER,
            max_weight INTEGER,
            icon_url TEXT
        );
        CREATE TABLE zone_fish_mapping (
            zone_id INTEGER,
            fish_id INTEGER,
            PRIMARY KEY (zone_id, fish_id)
        );
        CREATE TABLE baits (
            bait_id INTEGER PRIMARY KEY,
            description TEXT
        );
        CREATE TABLE rods (
            rod_id INTEGER PRIMARY KEY,
            purchase_cost INTEGER
        );
        CREATE TABLE gacha_pools (
            gacha_pool_id INTEGER PRIMARY KEY,
            name TEXT,
            is_limited_time INTEGER,
            open_until TEXT
        );
        CREATE TABLE shops (
            shop_id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            shop_type TEXT,
            is_active INTEGER,
            sort_order INTEGER
        );
        CREATE TABLE shop_items (
            item_id INTEGER PRIMARY KEY,
            shop_id INTEGER,
            name TEXT,
            description TEXT,
            category TEXT,
            per_user_limit INTEGER,
            is_active INTEGER,
            sort_order INTEGER
        );
        CREATE TABLE shop_item_costs (
            cost_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            cost_type TEXT,
            cost_amount INTEGER,
            cost_item_id INTEGER,
            cost_relation TEXT,
            quality_level INTEGER
        );
        CREATE TABLE shop_item_rewards (
            reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            reward_type TEXT,
            reward_item_id INTEGER,
            reward_quantity INTEGER,
            reward_refine_level INTEGER,
            quality_level INTEGER
        );
        INSERT INTO fish VALUES (1, 'old', '', 1, 1, 1, 2, NULL);
        INSERT INTO baits VALUES (14, 'old');
        INSERT INTO rods VALUES (4, NULL), (5, NULL);
        INSERT INTO gacha_pools VALUES
            (5, 'limited-a', 1, 'future'),
            (6, 'limited-b', 1, 'future');
        """
    )
    return connection


def test_catalog_sync_migration_matches_primary_instance_data():
    connection = _database()
    migration = _load_migration()

    migration.up(connection.cursor())
    migration.up(connection.cursor())

    assert connection.execute(
        "SELECT name, rarity, base_value FROM fish WHERE fish_id = 113"
    ).fetchone() == ("数学分析?", 8, 50)
    assert connection.execute(
        "SELECT COUNT(*) FROM zone_fish_mapping WHERE zone_id = 4 AND fish_id = 113"
    ).fetchone()[0] == 1
    assert connection.execute(
        "SELECT description FROM baits WHERE bait_id = 14"
    ).fetchone()[0] == "神秘的鱼饵"
    assert dict(
        connection.execute(
            "SELECT rod_id, purchase_cost FROM rods ORDER BY rod_id"
        )
    ) == {4: 80000, 5: 300000}
    assert connection.execute(
        "SELECT COUNT(*) FROM shop_items WHERE item_id BETWEEN 13 AND 18"
    ).fetchone()[0] == 6
    assert connection.execute(
        "SELECT cost_type, cost_item_id FROM shop_item_costs WHERE item_id = 17"
    ).fetchone() == ("fish", 113)


def test_catalog_sync_skips_empty_fresh_database():
    connection = _database()
    connection.execute("DELETE FROM fish")

    _load_migration().up(connection.cursor())

    assert connection.execute("SELECT COUNT(*) FROM fish").fetchone()[0] == 0

from __future__ import annotations

import importlib.util
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from astrbot_plugin_fishing.core.domain.models import MarketListing
from astrbot_plugin_fishing.core.economy import (
    fish_stack_total_value,
    fish_stack_unit_value,
)
from astrbot_plugin_fishing.core.repositories.sqlite_inventory_repo import (
    SqliteInventoryRepository,
)
from astrbot_plugin_fishing.core.repositories.sqlite_market_repo import (
    SqliteMarketRepository,
)


def _load_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "core"
        / "database"
        / "migrations"
        / "043_persist_fish_unit_value.py"
    )
    spec = importlib.util.spec_from_file_location("fish_value_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            nickname TEXT
        );
        CREATE TABLE fish (
            fish_id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            rarity INTEGER,
            base_value INTEGER
        );
        CREATE TABLE user_fish_inventory (
            user_id TEXT NOT NULL,
            fish_id INTEGER NOT NULL,
            quality_level INTEGER DEFAULT 0,
            quantity INTEGER DEFAULT 0,
            no_sell_until DATETIME,
            PRIMARY KEY (user_id, fish_id, quality_level)
        );
        CREATE TABLE user_aquarium (
            user_id TEXT NOT NULL,
            fish_id INTEGER NOT NULL,
            quality_level INTEGER DEFAULT 0,
            quantity INTEGER DEFAULT 0,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, fish_id, quality_level)
        );
        CREATE TABLE market (
            market_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item_type TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price INTEGER NOT NULL,
            listed_at TEXT NOT NULL,
            expires_at TEXT,
            refine_level INTEGER DEFAULT 1,
            seller_nickname TEXT,
            item_name TEXT,
            item_description TEXT,
            item_instance_id INTEGER,
            is_anonymous INTEGER DEFAULT 0,
            quality_level INTEGER DEFAULT 0
        );
        CREATE TABLE rods (rod_id INTEGER PRIMARY KEY, name TEXT, description TEXT);
        CREATE TABLE accessories (
            accessory_id INTEGER PRIMARY KEY, name TEXT, description TEXT
        );
        CREATE TABLE items (item_id INTEGER PRIMARY KEY, name TEXT, description TEXT);
        CREATE TABLE commodities (
            commodity_id INTEGER PRIMARY KEY, name TEXT, description TEXT
        );
        INSERT INTO users VALUES ('u1', 'seller');
        INSERT INTO fish VALUES (1, 'fish', 'desc', 1, 10);
        """
    )
    migration = _load_migration()
    migration.up(connection.cursor())
    migration.up(connection.cursor())
    connection.commit()
    connection.close()


def test_fish_value_helpers_use_persisted_unit_value_and_quality():
    item = SimpleNamespace(unit_value=15.5, quality_level=1, quantity=3)
    assert fish_stack_unit_value(10, item) == pytest.approx(31)
    assert fish_stack_total_value(10, item) == 93


def test_inventory_merges_unit_values_by_quantity(tmp_path):
    database = tmp_path / "fish.db"
    _create_database(database)
    repo = SqliteInventoryRepository(str(database))

    repo.add_fish_to_inventory("u1", 1, quantity=2, unit_value=20)
    repo.add_fish_to_inventory("u1", 1, quantity=1, unit_value=5)

    item = repo.get_fish_inventory("u1")[0]
    assert item.quantity == 3
    assert item.unit_value == pytest.approx(15)
    assert repo.get_fish_inventory_value("u1") == pytest.approx(45)

    repo.update_fish_quantity("u1", 1, delta=1)
    item = repo.get_fish_inventory("u1")[0]
    assert item.quantity == 4
    assert item.unit_value == pytest.approx(13.75)


def test_old_insert_without_unit_value_remains_compatible(tmp_path):
    database = tmp_path / "fish.db"
    _create_database(database)
    connection = sqlite3.connect(database)
    connection.execute(
        """
        INSERT INTO user_fish_inventory (
            user_id, fish_id, quality_level, quantity
        ) VALUES ('u1', 1, 1, 2)
        """
    )
    connection.commit()
    connection.close()

    item = SqliteInventoryRepository(str(database)).get_fish_inventory("u1")[0]
    assert item.unit_value is None
    assert fish_stack_total_value(10, item) == 40


def test_market_listing_round_trip_preserves_unit_value(tmp_path):
    database = tmp_path / "fish.db"
    _create_database(database)
    repo = SqliteMarketRepository(str(database))
    listing = MarketListing(
        market_id=0,
        user_id="u1",
        seller_nickname="seller",
        item_type="fish",
        item_id=1,
        item_name="fish",
        item_description="desc",
        quantity=2,
        price=100,
        listed_at=__import__("datetime").datetime.now(),
        quality_level=1,
        unit_value=25,
    )

    repo.add_listing(listing)
    loaded = repo.get_listing_by_id(1)

    assert loaded.quality_level == 1
    assert loaded.unit_value == pytest.approx(25)

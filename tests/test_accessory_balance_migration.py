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
        / "045_rebalance_accessories.py"
    )
    spec = importlib.util.spec_from_file_location(
        "accessory_balance_migration", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_accessory_balance_migration_is_idempotent():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE accessories (
            accessory_id INTEGER PRIMARY KEY,
            bonus_fish_quality_modifier REAL,
            bonus_fish_quantity_modifier REAL,
            bonus_rare_fish_chance REAL,
            bonus_coin_modifier REAL,
            fishing_cooldown_modifier REAL,
            other_bonus_description TEXT
        )
        """
    )
    connection.executemany(
        "INSERT INTO accessories (accessory_id) VALUES (?)",
        [(accessory_id,) for accessory_id in range(1, 8)],
    )
    migration = _load_migration()

    migration.up(connection.cursor())
    migration.up(connection.cursor())

    sea_heart = connection.execute(
        """
        SELECT bonus_fish_quality_modifier,
               bonus_fish_quantity_modifier,
               bonus_rare_fish_chance,
               bonus_coin_modifier,
               fishing_cooldown_modifier
        FROM accessories WHERE accessory_id = 4
        """
    ).fetchone()
    electric = connection.execute(
        """
        SELECT bonus_fish_quantity_modifier, fishing_cooldown_modifier
        FROM accessories WHERE accessory_id = 7
        """
    ).fetchone()
    assert sea_heart == (1.1, 1.04, 0.03, 1.1, 0.75)
    assert electric == (1.12, 0.75)

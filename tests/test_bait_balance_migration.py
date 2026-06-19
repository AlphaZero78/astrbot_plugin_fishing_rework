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
        / "044_rebalance_baits.py"
    )
    spec = importlib.util.spec_from_file_location("bait_balance_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bait_balance_migration_is_idempotent_and_fixes_consumption_flags():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE baits (
            bait_id INTEGER PRIMARY KEY,
            effect_description TEXT,
            success_rate_modifier REAL,
            rare_chance_modifier REAL,
            garbage_reduction_modifier REAL,
            value_modifier REAL,
            quantity_modifier REAL,
            is_consumable INTEGER
        )
        """
    )
    connection.executemany(
        "INSERT INTO baits (bait_id, is_consumable) VALUES (?, 1)",
        [(bait_id,) for bait_id in range(1, 15)],
    )
    migration = _load_migration()

    migration.up(connection.cursor())
    migration.up(connection.cursor())

    bait_6 = connection.execute(
        """
        SELECT rare_chance_modifier, is_consumable
        FROM baits WHERE bait_id = 6
        """
    ).fetchone()
    bait_14 = connection.execute(
        """
        SELECT success_rate_modifier, rare_chance_modifier,
               value_modifier, quantity_modifier, is_consumable
        FROM baits WHERE bait_id = 14
        """
    ).fetchone()
    assert bait_6 == (0.03, 0)
    assert bait_14 == (0.25, 0.25, 1.3, 1.05, 1)

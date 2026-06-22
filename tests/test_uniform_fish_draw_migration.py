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
        / "048_rebalance_zone_costs_for_uniform_fish_draw.py"
    )
    spec = importlib.util.spec_from_file_location(
        "uniform_fish_draw_migration", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_uniform_fish_draw_migration_updates_zone_costs_idempotently():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE fishing_zones (
            id INTEGER PRIMARY KEY,
            fishing_cost INTEGER
        )
        """
    )
    connection.executemany(
        "INSERT INTO fishing_zones (id, fishing_cost) VALUES (?, ?)",
        [(1, 6), (2, 32), (3, 509), (4, 1308)],
    )

    migration = _load_migration()
    migration.up(connection.cursor())
    migration.up(connection.cursor())

    assert dict(
        connection.execute(
            "SELECT id, fishing_cost FROM fishing_zones ORDER BY id"
        )
    ) == {1: 5, 2: 25, 3: 300, 4: 620}

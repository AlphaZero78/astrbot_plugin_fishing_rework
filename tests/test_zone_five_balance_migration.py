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
        / "051_rebalance_zone_five.py"
    )
    spec = importlib.util.spec_from_file_location(
        "zone_five_balance_migration", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_zone_five_distribution_is_updated_without_losing_other_config():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE fishing_zones (
            id INTEGER PRIMARY KEY,
            configs TEXT
        )
        """
    )
    connection.execute(
        "INSERT INTO fishing_zones (id, configs) VALUES (5, ?)",
        (json.dumps({"rarity_distribution": [1, 0, 0, 0, 0, 0], "x": 1}),),
    )

    migration = _load_migration()
    migration.up(connection.cursor())
    migration.up(connection.cursor())

    config = json.loads(
        connection.execute(
            "SELECT configs FROM fishing_zones WHERE id = 5"
        ).fetchone()[0]
    )
    assert config["rarity_distribution"] == [
        0.05,
        0.10,
        0.15,
        0.25,
        0.3075,
        0.1425,
    ]
    assert config["x"] == 1


def test_zone_five_migration_is_safe_when_zone_is_absent():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE fishing_zones (
            id INTEGER PRIMARY KEY,
            configs TEXT
        )
        """
    )

    _load_migration().up(connection.cursor())

    assert connection.execute(
        "SELECT COUNT(*) FROM fishing_zones"
    ).fetchone()[0] == 0

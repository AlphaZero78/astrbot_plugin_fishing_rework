from __future__ import annotations

import importlib.util
from pathlib import Path
import sqlite3

import pytest

from astrbot_plugin_fishing.core.utils import calculate_after_refine


def _load_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "core"
        / "database"
        / "migrations"
        / "046_align_rod_tiers_and_specialist_accessories.py"
    )
    spec = importlib.util.spec_from_file_location(
        "equipment_tier_balance_migration", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_equipment_tier_balance_migration_is_idempotent():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE rods (
            rod_id INTEGER PRIMARY KEY,
            rarity INTEGER,
            bonus_fish_quality_modifier REAL,
            bonus_fish_quantity_modifier REAL,
            bonus_rare_fish_chance REAL
        );
        CREATE TABLE accessories (
            accessory_id INTEGER PRIMARY KEY,
            bonus_fish_quality_modifier REAL,
            bonus_fish_quantity_modifier REAL,
            bonus_rare_fish_chance REAL,
            bonus_coin_modifier REAL,
            fishing_cooldown_modifier REAL,
            other_bonus_description TEXT
        );
        CREATE TABLE gacha_pools (
            gacha_pool_id INTEGER PRIMARY KEY,
            cost_coins INTEGER
        );
        CREATE TABLE fishing_zones (
            id INTEGER PRIMARY KEY,
            fishing_cost INTEGER
        );
        """
    )
    connection.executemany(
        "INSERT INTO rods (rod_id, rarity) VALUES (?, ?)",
        [(rod_id, rod_id) for rod_id in range(1, 7)],
    )
    connection.executemany(
        "INSERT INTO accessories (accessory_id) VALUES (?)",
        [(accessory_id,) for accessory_id in range(1, 8)],
    )
    connection.executemany(
        "INSERT INTO gacha_pools (gacha_pool_id) VALUES (?)",
        [(pool_id,) for pool_id in range(4, 8)],
    )
    connection.executemany(
        "INSERT INTO fishing_zones (id) VALUES (?)",
        [(zone_id,) for zone_id in range(1, 5)],
    )

    migration = _load_migration()
    migration.up(connection.cursor())
    migration.up(connection.cursor())

    rods = connection.execute(
        """
        SELECT rod_id, rarity, bonus_fish_quality_modifier,
               bonus_fish_quantity_modifier, bonus_rare_fish_chance
        FROM rods ORDER BY rod_id
        """
    ).fetchall()
    for previous, current in zip(rods[1:-1], rods[2:]):
        for previous_value, current_value in zip(previous[2:], current[2:]):
            assert current_value == pytest.approx(
                calculate_after_refine(
                    previous_value,
                    refine_level=5,
                    rarity=previous[1],
                )
            )

    common_accessories = connection.execute(
        """
        SELECT accessory_id, bonus_fish_quality_modifier,
               bonus_fish_quantity_modifier, bonus_rare_fish_chance,
               bonus_coin_modifier
        FROM accessories WHERE accessory_id BETWEEN 1 AND 4
        ORDER BY accessory_id
        """
    ).fetchall()
    for previous, current, previous_rarity in zip(
        common_accessories[:-1],
        common_accessories[1:],
        (2, 3, 4),
    ):
        for previous_value, current_value in zip(previous[1:], current[1:]):
            assert current_value == pytest.approx(
                calculate_after_refine(
                    previous_value,
                    refine_level=5,
                    rarity=previous_rarity,
                )
            )

    common_six_star = tuple(
        calculate_after_refine(value, refine_level=5, rarity=5)
        for value in common_accessories[-1][1:]
    )
    specialists = connection.execute(
        """
        SELECT accessory_id, bonus_fish_quality_modifier,
               bonus_fish_quantity_modifier, bonus_rare_fish_chance,
               bonus_coin_modifier, fishing_cooldown_modifier
        FROM accessories WHERE accessory_id BETWEEN 5 AND 7
        ORDER BY accessory_id
        """
    ).fetchall()
    probe, lure, electric = specialists
    assert probe[1] == pytest.approx(1.35)
    assert probe[2:5] == pytest.approx(common_six_star[1:])
    assert lure[1:3] == pytest.approx(common_six_star[:2])
    assert lure[3] == pytest.approx(0.14)
    assert lure[4] == pytest.approx(common_six_star[3])
    assert electric[1] == pytest.approx(common_six_star[0])
    assert electric[2] == pytest.approx(1.12)
    assert electric[3:5] == pytest.approx(common_six_star[2:])
    assert [row[5] for row in specialists] == pytest.approx([0.70] * 3)

    assert dict(
        connection.execute(
            "SELECT gacha_pool_id, cost_coins FROM gacha_pools"
        )
    ) == {4: 13, 5: 1000, 6: 1000, 7: 20000}
    assert dict(
        connection.execute(
            "SELECT id, fishing_cost FROM fishing_zones"
        )
    ) == {1: 6, 2: 32, 3: 509, 4: 1308}

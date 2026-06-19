from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sqlite3
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT.parent))

analytics = importlib.import_module(f"{REPO_ROOT.name}.core.analytics")
game_config = importlib.import_module(f"{REPO_ROOT.name}.core.config.game_config")
bait_mechanics = importlib.import_module(f"{REPO_ROOT.name}.core.mechanics")
FishingScenario = analytics.FishingScenario
GachaEntry = analytics.GachaEntry
expected_fishing_return = analytics.expected_fishing_return
expected_gacha_return = analytics.expected_gacha_return
SELL_PRICE_BY_RARITY = game_config.SELL_PRICE_BY_RARITY
DEFAULT_RARE_BONUS_CAP = game_config.DEFAULT_RARE_BONUS_CAP
bait_cost_per_attempt = bait_mechanics.bait_cost_per_attempt


def load_fish_values(
    connection: sqlite3.Connection, zone_id: int
) -> dict[int, list[float]]:
    rows = connection.execute(
        """
        SELECT f.rarity, f.base_value
        FROM zone_fish_mapping zfm
        JOIN fish f ON f.fish_id = zfm.fish_id
        WHERE zfm.zone_id = ?
        ORDER BY f.rarity, f.fish_id
        """,
        (zone_id,),
    ).fetchall()
    result: dict[int, list[float]] = {}
    for rarity, base_value in rows:
        result.setdefault(int(rarity), []).append(float(base_value))
    return result


def load_catalog_values(connection: sqlite3.Connection) -> dict[tuple[str, int], float]:
    values: dict[tuple[str, int], float] = {}
    queries = {
        "rod": "SELECT rod_id, COALESCE(purchase_cost, 0) FROM rods",
        "bait": "SELECT bait_id, COALESCE(cost, 0) FROM baits",
        "item": "SELECT item_id, COALESCE(cost, 0) FROM items",
    }
    for item_type, query in queries.items():
        for item_id, value in connection.execute(query):
            values[(item_type, int(item_id))] = float(value)
    for item_id, rarity in connection.execute(
        "SELECT accessory_id, rarity FROM accessories"
    ):
        values[("accessory", int(item_id))] = float(
            SELL_PRICE_BY_RARITY.get(str(rarity), 0)
        )
    return values


def analyze(database: Path) -> dict[str, list[dict[str, float | int | str]]]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        zones = []
        zone_inputs = {}
        for row in connection.execute(
            "SELECT id, name, configs, fishing_cost FROM fishing_zones ORDER BY id"
        ):
            config = json.loads(row["configs"] or "{}")
            distribution = config.get("rarity_distribution")
            if not distribution:
                continue
            fish_values = load_fish_values(connection, row["id"])
            zone_inputs[row["id"]] = (distribution, fish_values, row["fishing_cost"])
            result = expected_fishing_return(
                distribution,
                fish_values,
                FishingScenario(
                    fishing_cost=row["fishing_cost"],
                    cooldown_seconds=180,
                ),
            )
            zones.append({"id": row["id"], "name": row["name"], **result})

        baits = []
        if zone_inputs:
            for bait in connection.execute("SELECT * FROM baits ORDER BY cost, bait_id"):
                preferred_zone_id = (
                    4 if bait["required_rod_rarity"] >= 4 else 3
                )
                bait_zone_id = (
                    preferred_zone_id
                    if preferred_zone_id in zone_inputs
                    else next(iter(zone_inputs))
                )
                distribution, fish_values, fishing_cost = zone_inputs[bait_zone_id]
                baseline = expected_fishing_return(
                    distribution,
                    fish_values,
                    FishingScenario(
                        fishing_cost=fishing_cost,
                        cooldown_seconds=180,
                    ),
                )
                scenario = FishingScenario(
                    success_rate=min(0.7 + bait["success_rate_modifier"], 1.0),
                    quantity_modifier=bait["quantity_modifier"],
                    value_modifier=bait["value_modifier"],
                    rare_bonus=min(
                        bait["rare_chance_modifier"], DEFAULT_RARE_BONUS_CAP
                    ),
                    fishing_cost=fishing_cost,
                    consumable_cost=bait_cost_per_attempt(bait, 180),
                    cooldown_seconds=180,
                    garbage_reduction=bait["garbage_reduction_modifier"],
                )
                result = expected_fishing_return(
                    distribution, fish_values, scenario
                )
                baits.append(
                    {
                        "id": bait["bait_id"],
                        "name": bait["name"],
                        "zone_id": bait_zone_id,
                        "cost_per_attempt": scenario.consumable_cost,
                        "gross_uplift": (
                            result["gross_value"] / baseline["gross_value"] - 1
                        ),
                        "net_change": (
                            result["net_value"] - baseline["net_value"]
                        ),
                        **result,
                    }
                )

        rods = []
        accessories = []
        equipment_zone_id = 4 if 4 in zone_inputs else next(iter(zone_inputs), None)
        if equipment_zone_id is not None:
            distribution, fish_values, fishing_cost = zone_inputs[equipment_zone_id]
            baseline = expected_fishing_return(
                distribution,
                fish_values,
                FishingScenario(
                    fishing_cost=fishing_cost,
                    cooldown_seconds=180,
                ),
            )
            for rod in connection.execute("SELECT * FROM rods ORDER BY rarity, rod_id"):
                result = expected_fishing_return(
                    distribution,
                    fish_values,
                    FishingScenario(
                        quantity_modifier=rod["bonus_fish_quantity_modifier"],
                        quality_modifier=rod["bonus_fish_quality_modifier"],
                        rare_bonus=min(
                            rod["bonus_rare_fish_chance"],
                            DEFAULT_RARE_BONUS_CAP,
                        ),
                        fishing_cost=fishing_cost,
                        cooldown_seconds=180,
                    ),
                )
                rods.append(
                    {
                        "id": rod["rod_id"],
                        "name": rod["name"],
                        "rarity": rod["rarity"],
                        "gross_uplift": (
                            result["gross_value"] / baseline["gross_value"] - 1
                        ),
                        "net_hour_uplift": (
                            result["net_value_per_hour"]
                            / baseline["net_value_per_hour"]
                            - 1
                        ),
                        **result,
                    }
                )
            for accessory in connection.execute(
                "SELECT * FROM accessories ORDER BY rarity, accessory_id"
            ):
                result = expected_fishing_return(
                    distribution,
                    fish_values,
                    FishingScenario(
                        quantity_modifier=accessory[
                            "bonus_fish_quantity_modifier"
                        ],
                        value_modifier=accessory["bonus_coin_modifier"],
                        quality_modifier=accessory[
                            "bonus_fish_quality_modifier"
                        ],
                        rare_bonus=min(
                            accessory["bonus_rare_fish_chance"],
                            DEFAULT_RARE_BONUS_CAP,
                        ),
                        fishing_cost=fishing_cost,
                        cooldown_seconds=(
                            180 * accessory["fishing_cooldown_modifier"]
                        ),
                    ),
                )
                accessories.append(
                    {
                        "id": accessory["accessory_id"],
                        "name": accessory["name"],
                        "rarity": accessory["rarity"],
                        "gross_uplift": (
                            result["gross_value"] / baseline["gross_value"] - 1
                        ),
                        "net_hour_uplift": (
                            result["net_value_per_hour"]
                            / baseline["net_value_per_hour"]
                            - 1
                        ),
                        **result,
                    }
                )

        catalog_values = load_catalog_values(connection)
        pools = []
        for pool in connection.execute(
            "SELECT * FROM gacha_pools ORDER BY gacha_pool_id"
        ):
            entries = [
                GachaEntry(
                    item_type=item["item_type"],
                    item_id=item["item_id"],
                    quantity=item["quantity"],
                    weight=item["weight"],
                )
                for item in connection.execute(
                    """
                    SELECT item_type, item_id, quantity, weight
                    FROM gacha_pool_items
                    WHERE gacha_pool_id = ?
                    ORDER BY gacha_pool_item_id
                    """,
                    (pool["gacha_pool_id"],),
                )
            ]
            result = expected_gacha_return(
                entries, catalog_values, pool["cost_coins"]
            )
            pools.append(
                {
                    "id": pool["gacha_pool_id"],
                    "name": pool["name"],
                    **result,
                }
            )
        return {
            "zones": zones,
            "baits": baits,
            "rods": rods,
            "accessories": accessories,
            "gacha_pools": pools,
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze fishing-zone and gacha expected returns."
    )
    parser.add_argument("database", type=Path, help="Path to fish.db")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    report = analyze(args.database)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print("Fishing zones")
    for row in report["zones"]:
        print(
            f"{row['id']}: {row['name']} | gross={row['gross_value']:.2f} "
            f"net={row['net_value']:.2f} | return={row['return_ratio']:.2f}x "
            f"| net/hour={row['net_value_per_hour']:.2f}"
        )
    print("\nBaits (baseline zone follows rod requirement)")
    for row in report["baits"]:
        print(
            f"{row['id']}: {row['name']} | zone={row['zone_id']} "
            f"| uplift={row['gross_uplift']:.1%} "
            f"| cost/attempt={row['cost_per_attempt']:.2f} "
            f"| net change={row['net_change']:.2f}"
        )
    print("\nRods (zone 4 baseline)")
    for row in report["rods"]:
        print(
            f"{row['id']}: {row['name']} | rarity={row['rarity']} "
            f"| gross uplift={row['gross_uplift']:.1%} "
            f"| net/hour uplift={row['net_hour_uplift']:.1%}"
        )
    print("\nAccessories (zone 4 baseline)")
    for row in report["accessories"]:
        print(
            f"{row['id']}: {row['name']} | rarity={row['rarity']} "
            f"| gross uplift={row['gross_uplift']:.1%} "
            f"| net/hour uplift={row['net_hour_uplift']:.1%}"
        )
    print("\nGacha pools")
    for row in report["gacha_pools"]:
        print(
            f"{row['id']}: {row['name']} | gross={row['gross_value']:.2f} "
            f"net={row['net_value']:.2f} | return={row['return_ratio']:.2f}x "
            f"| unresolved={row['unresolved_probability']:.2%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import sqlite3


ROD_BALANCE = {
    1: (1.0, 1.0, 0.0),
    2: (1.02, 1.01, 0.01),
    3: (1.032, 1.016, 0.016),
    4: (1.0512, 1.0256, 0.0256),
    5: (1.075776, 1.037888, 0.037888),
    6: (1.10002432, 1.05001216, 0.05001216),
}


ACCESSORY_BALANCE = {
    1: (
        1.03,
        1.01,
        0.005,
        1.02,
        1.0,
        "提供基础的均衡渔获加成",
    ),
    2: (
        1.048,
        1.016,
        0.008,
        1.032,
        1.0,
        "通用属性约等于幸运四叶草精炼5",
    ),
    3: (
        1.0768,
        1.0256,
        0.0128,
        1.0512,
        1.0,
        "通用属性约等于渔夫的戒指精炼5",
    ),
    4: (
        1.113664,
        1.037888,
        0.018944,
        1.075776,
        0.80,
        "通用属性约等于丰收号角精炼5，并减少钓鱼等待时间20%",
    ),
    5: (
        1.35,
        1.05001216,
        0.02500608,
        1.10002432,
        0.70,
        "专精高品质渔获，并减少钓鱼等待时间30%",
    ),
    6: (
        1.15003648,
        1.05001216,
        0.14,
        1.10002432,
        0.70,
        "专精稀有鱼权重，并减少钓鱼等待时间30%",
    ),
    7: (
        1.15003648,
        1.12,
        0.02500608,
        1.10002432,
        0.70,
        "专精渔获数量，并减少钓鱼等待时间30%",
    ),
}


GACHA_COSTS = {
    4: 13,
    5: 1000,
    6: 1000,
    7: 20000,
}

ZONE_COSTS = {
    1: 6,
    2: 32,
    3: 509,
    4: 1308,
}


def up(cursor: sqlite3.Cursor):
    for rod_id, values in ROD_BALANCE.items():
        cursor.execute(
            """
            UPDATE rods
            SET bonus_fish_quality_modifier = ?,
                bonus_fish_quantity_modifier = ?,
                bonus_rare_fish_chance = ?
            WHERE rod_id = ?
            """,
            (*values, rod_id),
        )

    for accessory_id, values in ACCESSORY_BALANCE.items():
        cursor.execute(
            """
            UPDATE accessories
            SET bonus_fish_quality_modifier = ?,
                bonus_fish_quantity_modifier = ?,
                bonus_rare_fish_chance = ?,
                bonus_coin_modifier = ?,
                fishing_cooldown_modifier = ?,
                other_bonus_description = ?
            WHERE accessory_id = ?
            """,
            (*values, accessory_id),
        )

    for pool_id, cost in GACHA_COSTS.items():
        cursor.execute(
            "UPDATE gacha_pools SET cost_coins = ? WHERE gacha_pool_id = ?",
            (cost, pool_id),
        )

    for zone_id, cost in ZONE_COSTS.items():
        cursor.execute(
            "UPDATE fishing_zones SET fishing_cost = ? WHERE id = ?",
            (cost, zone_id),
        )

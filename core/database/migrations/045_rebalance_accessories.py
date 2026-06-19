import sqlite3


ACCESSORY_BALANCE = {
    4: (
        1.10,
        1.04,
        0.03,
        1.10,
        0.75,
        "均衡提升渔获，并减少钓鱼等待时间25%",
    ),
    5: (
        1.35,
        1.05,
        0.04,
        1.06,
        0.75,
        "专精高品质渔获，并减少钓鱼等待时间25%",
    ),
    6: (
        1.08,
        1.02,
        0.14,
        1.12,
        0.75,
        "专精稀有鱼权重，并减少钓鱼等待时间25%",
    ),
    7: (
        1.08,
        1.12,
        0.04,
        1.06,
        0.75,
        "专精渔获数量，并减少钓鱼等待时间25%",
    ),
}


def up(cursor: sqlite3.Cursor):
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

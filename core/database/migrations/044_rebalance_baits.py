import sqlite3


BAIT_BALANCE = {
    1: ("本次钓鱼成功率 +2%", 0.02, 0.0, 0.0, 1.0, 1.0),
    2: ("本次钓鱼成功率 +2.5%", 0.025, 0.0, 0.0, 1.0, 1.0),
    3: ("本次钓鱼成功率 +3%", 0.03, 0.0, 0.0, 1.0, 1.0),
    4: ("本次钓鱼成功率 +5%", 0.05, 0.0, 0.0, 1.0, 1.0),
    5: ("本次钓鱼成功率 +8%", 0.08, 0.0, 0.0, 1.0, 1.0),
    6: ("稀有鱼权重加成 +3%；不会因钓鱼消耗", 0.0, 0.03, 0.0, 1.0, 1.0),
    7: (
        "本次成功率 +6%，稀有鱼权重加成 +3.5%",
        0.06,
        0.035,
        0.0,
        1.0,
        1.0,
    ),
    8: ("本次钓鱼成功率 +10%", 0.10, 0.0, 0.0, 1.0, 1.0),
    9: (
        "30分钟内，钓到价值低于5的鱼时有80%概率重抽一次",
        0.0,
        0.0,
        0.8,
        1.0,
        1.0,
    ),
    10: ("稀有鱼权重加成 +18%", 0.0, 0.18, 0.0, 1.0, 1.0),
    11: ("本次渔获重量和基础售价 +20%", 0.0, 0.0, 0.0, 1.2, 1.0),
    12: ("本次钓鱼成功率 +20%；不会因钓鱼消耗", 0.2, 0.0, 0.0, 1.0, 1.0),
    13: ("本次渔获重量和基础售价 +35%", 0.0, 0.0, 0.0, 1.35, 1.0),
    14: (
        "本次成功率 +25%，稀有鱼权重 +25%，垃圾鱼重抽率90%，"
        "重量和基础售价 ×1.3，渔获数量倍率 ×1.05",
        0.25,
        0.25,
        0.9,
        1.3,
        1.05,
    ),
}


def up(cursor: sqlite3.Cursor):
    for bait_id, values in BAIT_BALANCE.items():
        (
            effect_description,
            success_rate,
            rare_chance,
            garbage_reduction,
            value_modifier,
            quantity_modifier,
        ) = values
        cursor.execute(
            """
            UPDATE baits
            SET effect_description = ?,
                success_rate_modifier = ?,
                rare_chance_modifier = ?,
                garbage_reduction_modifier = ?,
                value_modifier = ?,
                quantity_modifier = ?
            WHERE bait_id = ?
            """,
            (
                effect_description,
                success_rate,
                rare_chance,
                garbage_reduction,
                value_modifier,
                quantity_modifier,
                bait_id,
            ),
        )
    cursor.execute(
        "UPDATE baits SET is_consumable = 0 WHERE bait_id IN (6, 12)"
    )
    cursor.execute(
        "UPDATE baits SET is_consumable = 1 WHERE bait_id NOT IN (6, 12)"
    )

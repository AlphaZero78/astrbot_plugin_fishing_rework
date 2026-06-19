import json
import sqlite3


ZONE_BALANCE = {
    1: {
        "name": "区域一：新手港湾",
        "description": "低成本入门水域，主要产出1-2星鱼。",
        "quota": 50,
        "distribution": [0.60, 0.30, 0.09, 0.01, 0.00, 0.00],
        "cost": 25,
    },
    2: {
        "name": "区域二：深海峡谷",
        "description": "稳定产出2-3星鱼，并有少量4-5星鱼。",
        "quota": 2000,
        "distribution": [0.35, 0.35, 0.21, 0.08, 0.01, 0.00],
        "cost": 140,
    },
    3: {
        "name": "区域三：传说之海",
        "description": "高投入高回报水域，可能出现6星及以上渔获。",
        "quota": 1000,
        "distribution": [0.20, 0.30, 0.20, 0.20, 0.09, 0.01],
        "cost": 2250,
    },
    4: {
        "name": "区域四：天井苑",
        "description": "顶级水域，稀有鱼密度与单次成本均为最高。",
        "quota": 1000,
        "distribution": [0.10, 0.30, 0.20, 0.20, 0.17, 0.03],
        "cost": 5800,
    },
}

GACHA_COSTS = {
    4: (10, "低成本常驻补给，期望回收接近抽取成本。"),
    5: (1250, "鱼竿与鱼饵限定池，按目录价值平衡。"),
    6: (700, "饰品与鱼饵限定池，按出售基准与实用价值平衡。"),
    7: (13000, "高阶装备、鱼饵与功能道具常驻池。"),
}

POOL_7_ITEMS = [
    ("rod", 6, 1, 1),
    ("accessory", 5, 1, 1),
    ("accessory", 6, 1, 1),
    ("accessory", 7, 1, 1),
    ("rod", 5, 1, 8),
    ("accessory", 4, 1, 8),
    ("bait", 14, 5, 50),
    ("bait", 13, 10, 300),
    ("bait", 10, 10, 300),
    ("bait", 11, 10, 500),
    ("bait", 8, 50, 900),
    ("item", 2, 1, 50),
    ("item", 12, 1, 20),
    ("item", 15, 1, 100),
]


def up(cursor: sqlite3.Cursor):
    for zone_id, zone in ZONE_BALANCE.items():
        cursor.execute(
            """
            INSERT INTO fishing_zones (
                id, name, description, daily_rare_fish_quota,
                rare_fish_caught_today, configs, is_active,
                requires_pass, fishing_cost
            )
            VALUES (?, ?, ?, ?, 0, ?, 1, 0, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                daily_rare_fish_quota = excluded.daily_rare_fish_quota,
                configs = excluded.configs,
                fishing_cost = excluded.fishing_cost
            """,
            (
                zone_id,
                zone["name"],
                zone["description"],
                zone["quota"],
                json.dumps(
                    {"rarity_distribution": zone["distribution"]},
                    ensure_ascii=False,
                ),
                zone["cost"],
            ),
        )

    cursor.execute(
        """
        INSERT INTO gacha_pools (
            gacha_pool_id, name, description, cost_coins,
            cost_premium_currency, is_limited_time, open_until
        )
        VALUES (7, '高级物资调度', ?, ?, 0, 0, NULL)
        ON CONFLICT(gacha_pool_id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            cost_coins = excluded.cost_coins
        """,
        (GACHA_COSTS[7][1], GACHA_COSTS[7][0]),
    )
    for pool_id, (cost, description) in GACHA_COSTS.items():
        cursor.execute(
            """
            UPDATE gacha_pools
            SET cost_coins = ?, description = ?
            WHERE gacha_pool_id = ?
            """,
            (cost, description, pool_id),
        )

    cursor.execute("DELETE FROM gacha_pool_items WHERE gacha_pool_id = 7")
    cursor.executemany(
        """
        INSERT INTO gacha_pool_items (
            gacha_pool_id, item_type, item_id, quantity, weight
        )
        VALUES (7, ?, ?, ?, ?)
        """,
        POOL_7_ITEMS,
    )

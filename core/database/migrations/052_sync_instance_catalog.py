import sqlite3


SPECIAL_SHOP_ITEMS = [
    (
        13, 2, "源矿钓竿",
        "以源矿核心驱动的高阶钓竿，能稳定放大多项渔获收益。",
        "general", 1,
    ),
    (
        14, 2, "探鱼器",
        "扫描水域回波，帮助渔夫发现更高品质的目标。",
        "general", 1,
    ),
    (
        15, 2, "诱鱼器",
        "释放稳定诱鱼波段，吸引更稀有的鱼靠近。",
        "general", 1,
    ),
    (
        16, 2, "电鱼器",
        "以可控电脉冲扰动鱼群，提高一次钓获的丰富度。",
        "general", 1,
    ),
    (
        17, 2, "源矿钓竿",
        "以源矿核心驱动的高阶钓竿，能稳定放大多项渔获收益。",
        "general", None,
    ),
    (
        18, 2, "海洋之心",
        "传说中的宝石，能与海洋生物沟通",
        "general", None,
    ),
]

SPECIAL_SHOP_COSTS = [
    (13, "premium", 7, None),
    (14, "premium", 7, None),
    (15, "premium", 7, None),
    (16, "premium", 7, None),
    (17, "fish", 1, 113),
    (18, "premium", 3, None),
]

SPECIAL_SHOP_REWARDS = [
    (13, "rod", 6),
    (14, "accessory", 5),
    (15, "accessory", 6),
    (16, "accessory", 7),
    (17, "rod", 6),
    (18, "accessory", 4),
]


def up(cursor: sqlite3.Cursor):
    """Sync catalog edits made in the primary instance back into migrations."""
    if cursor.execute("SELECT COUNT(*) FROM fish").fetchone()[0] == 0:
        return

    cursor.execute(
        """
        INSERT INTO fish (
            fish_id, name, description, rarity, base_value,
            min_weight, max_weight, icon_url
        )
        VALUES (113, '数学分析?', '一本书,但不值钱', 8, 50, 300, 500, NULL)
        ON CONFLICT(fish_id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            rarity = excluded.rarity,
            base_value = excluded.base_value,
            min_weight = excluded.min_weight,
            max_weight = excluded.max_weight
        """
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO zone_fish_mapping (zone_id, fish_id)
        VALUES (4, 113)
        """
    )
    cursor.execute(
        "UPDATE baits SET description = '神秘的鱼饵' WHERE bait_id = 14"
    )
    cursor.execute(
        "UPDATE rods SET purchase_cost = 80000 WHERE rod_id = 4"
    )
    cursor.execute(
        "UPDATE rods SET purchase_cost = 300000 WHERE rod_id = 5"
    )
    cursor.execute(
        """
        UPDATE gacha_pools
        SET name = '开服庆典寻访',
            is_limited_time = 0,
            open_until = NULL
        WHERE gacha_pool_id = 5
        """
    )
    cursor.execute(
        """
        UPDATE gacha_pools
        SET name = '开服庆典申领',
            is_limited_time = 0,
            open_until = NULL
        WHERE gacha_pool_id = 6
        """
    )

    cursor.execute(
        """
        INSERT INTO shops (
            shop_id, name, description, shop_type, is_active, sort_order
        )
        VALUES (2, '特别兑换', '能换到什么呢?', 'premium', 1, 100)
        ON CONFLICT(shop_id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            shop_type = excluded.shop_type,
            is_active = excluded.is_active,
            sort_order = excluded.sort_order
        """
    )
    for item_id, shop_id, name, description, category, user_limit in (
        SPECIAL_SHOP_ITEMS
    ):
        cursor.execute(
            """
            INSERT INTO shop_items (
                item_id, shop_id, name, description, category,
                per_user_limit, is_active, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, 100)
            ON CONFLICT(item_id) DO UPDATE SET
                shop_id = excluded.shop_id,
                name = excluded.name,
                description = excluded.description,
                category = excluded.category,
                per_user_limit = excluded.per_user_limit,
                is_active = excluded.is_active,
                sort_order = excluded.sort_order
            """,
            (item_id, shop_id, name, description, category, user_limit),
        )

    cursor.execute(
        "DELETE FROM shop_item_costs WHERE item_id BETWEEN 13 AND 18"
    )
    cursor.executemany(
        """
        INSERT INTO shop_item_costs (
            item_id, cost_type, cost_amount, cost_item_id,
            cost_relation, quality_level
        )
        VALUES (?, ?, ?, ?, 'and', 0)
        """,
        SPECIAL_SHOP_COSTS,
    )
    cursor.execute(
        "DELETE FROM shop_item_rewards WHERE item_id BETWEEN 13 AND 18"
    )
    cursor.executemany(
        """
        INSERT INTO shop_item_rewards (
            item_id, reward_type, reward_item_id, reward_quantity,
            reward_refine_level, quality_level
        )
        VALUES (?, ?, ?, 1, NULL, 0)
        """,
        SPECIAL_SHOP_REWARDS,
    )

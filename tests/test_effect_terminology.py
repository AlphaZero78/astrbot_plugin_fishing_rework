from astrbot_plugin_fishing.utils import format_accessory_or_rod


def test_equipment_effects_use_explicit_multiplier_terms():
    message = format_accessory_or_rod(
        {
            "instance_id": 1,
            "display_code": "A1",
            "name": "测试饰品",
            "rarity": 5,
            "is_equipped": True,
            "is_locked": False,
            "bonus_fish_quality_modifier": 1.30,
            "bonus_fish_quantity_modifier": 1.30,
            "bonus_rare_fish_chance": 0.05,
            "bonus_coin_modifier": 1.10,
            "fishing_cooldown_modifier": 0.75,
            "description": "测试描述",
        }
    )

    assert "高品质触发倍率: x1.30" in message
    assert "渔获数量倍率: x1.30" in message
    assert "稀有鱼权重加成: +5.00%" in message
    assert "渔获重量/基础价值倍率: x1.10" in message
    assert "钓鱼冷却倍率: x0.75 (等待时间-25%)" in message
    assert "鱼类数量加成" not in message

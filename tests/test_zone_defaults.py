from __future__ import annotations

from types import SimpleNamespace

from astrbot_plugin_fishing.core.config import (
    build_default_zone_fish_mappings,
)


def test_default_zone_mapping_rules_are_data_driven():
    fishes = [
        SimpleNamespace(fish_id=1, rarity=1, base_value=1),
        SimpleNamespace(fish_id=2, rarity=1, base_value=10),
        SimpleNamespace(fish_id=3, rarity=2, base_value=35),
        SimpleNamespace(fish_id=4, rarity=5, base_value=800),
        SimpleNamespace(fish_id=5, rarity=6, base_value=45000),
        SimpleNamespace(fish_id=6, rarity=8, base_value=50),
    ]

    mappings = build_default_zone_fish_mappings(fishes)

    assert mappings[1] == [1, 2, 3, 4]
    assert mappings[2] == [1, 2, 3, 4]
    assert mappings[3] == [1, 2, 3, 4, 5, 6]
    assert mappings[4] == [1, 3, 4, 5, 6]


def test_math_analysis_is_only_added_to_the_intended_default_zone():
    fishes = [
        SimpleNamespace(
            fish_id=113,
            name="数学分析?",
            rarity=8,
            base_value=50,
        )
    ]

    mappings = build_default_zone_fish_mappings(fishes)

    assert 113 not in mappings[3]
    assert mappings[4] == [113]


class _InventoryRepo:
    def __init__(self):
        self.mappings = {1: [99], 2: [], 3: [], 4: []}

    def get_specific_fish_ids_for_zone(self, zone_id):
        return self.mappings[zone_id]

    def update_specific_fish_for_zone(self, zone_id, fish_ids):
        self.mappings[zone_id] = list(fish_ids)


def test_data_setup_preserves_custom_mapping_and_fills_empty_zones():
    from astrbot_plugin_fishing.core.services.data_setup_service import (
        DataSetupService,
    )

    fishes = [
        SimpleNamespace(fish_id=1, rarity=1, base_value=1),
        SimpleNamespace(fish_id=2, rarity=2, base_value=35),
        SimpleNamespace(fish_id=3, rarity=6, base_value=45000),
    ]
    inventory = _InventoryRepo()
    service = DataSetupService(None, None, None, inventory)

    service._ensure_default_zone_fish_mappings(fishes)

    assert inventory.mappings[1] == [99]
    assert inventory.mappings[2] == [1, 2]
    assert inventory.mappings[3] == [1, 2, 3]
    assert inventory.mappings[4] == [1, 2, 3]

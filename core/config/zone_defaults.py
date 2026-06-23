from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def build_default_zone_fish_mappings(
    fishes: Iterable[Any],
) -> dict[int, list[int]]:
    """Build default fish mappings without depending on database IDs ranges."""
    fish_list = list(fishes)
    return {
        1: [
            fish.fish_id
            for fish in fish_list
            if 1 <= int(fish.rarity) <= 5
        ],
        2: [
            fish.fish_id
            for fish in fish_list
            if 1 <= int(fish.rarity) <= 5
        ],
        3: [
            fish.fish_id
            for fish in fish_list
            if str(getattr(fish, "name", "")) != "数学分析?"
        ],
        4: [
            fish.fish_id
            for fish in fish_list
            if int(fish.rarity) >= 2 or int(fish.base_value) <= 2
        ],
    }

import sqlite3
from types import SimpleNamespace

from astrbot_plugin_fishing.core.repositories.sqlite_item_template_repo import (
    SqliteItemTemplateRepository,
)
from astrbot_plugin_fishing.core.services import fishing_service
from astrbot_plugin_fishing.core.utils import get_fish_template


def test_same_rarity_selection_uses_uniform_choice(monkeypatch):
    fishes = [
        SimpleNamespace(name="数学分析?", base_value=50),
        SimpleNamespace(name="世界之鱼", base_value=500000),
        SimpleNamespace(name="创世神鲲", base_value=1000000),
    ]
    captured = {}

    def fake_choice(values):
        captured["values"] = values
        return values[0]

    monkeypatch.setattr("astrbot_plugin_fishing.core.utils.random.choice", fake_choice)
    selected = get_fish_template(fishes, coins_chance=999)

    assert selected.name == "数学分析?"
    assert captured["values"] == fishes


def test_runtime_high_rarity_selection_uses_geometric_decay(monkeypatch):
    service = fishing_service.FishingService.__new__(
        fishing_service.FishingService
    )
    service.item_template_repo = SimpleNamespace(
        get_fish_by_id=lambda fish_id: {
            1: SimpleNamespace(rarity=6),
            2: SimpleNamespace(rarity=7),
            3: SimpleNamespace(rarity=8),
        }[fish_id]
    )
    captured = {}

    def fake_choices(values, weights, k):
        captured["values"] = values
        captured["weights"] = weights
        captured["k"] = k
        return [values[-1]]

    monkeypatch.setattr(
        "astrbot_plugin_fishing.core.services.fishing_service.random.choices",
        fake_choices,
    )
    rarity = service._get_random_high_rarity(
        SimpleNamespace(specific_fish_ids=[1, 2, 3])
    )

    assert rarity == 8
    assert captured == {
        "values": [6, 7, 8],
        "weights": [1.0, 0.5, 0.25],
        "k": 1,
    }


def test_random_fish_fallback_respects_requested_rarity(tmp_path):
    database = tmp_path / "fish.db"
    connection = sqlite3.connect(database)
    connection.execute(
        """
        CREATE TABLE fish (
            fish_id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            rarity INTEGER,
            base_value INTEGER,
            min_weight REAL,
            max_weight REAL,
            icon_url TEXT
        )
        """
    )
    connection.executemany(
        """
        INSERT INTO fish (
            fish_id, name, description, rarity, base_value,
            min_weight, max_weight, icon_url
        )
        VALUES (?, ?, '', ?, ?, 1, 2, '')
        """,
        [
            (1, "six-star", 6, 600),
            (2, "eight-star-a", 8, 50),
            (3, "eight-star-b", 8, 1000000),
        ],
    )
    connection.commit()
    connection.close()

    repository = SqliteItemTemplateRepository(str(database))
    for _ in range(20):
        fish = repository.get_random_fish(8)
        assert fish is not None
        assert fish.rarity == 8

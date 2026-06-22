from __future__ import annotations

from pathlib import Path
import sqlite3

from astrbot_plugin_fishing.core.database.migration import run_migrations
from astrbot_plugin_fishing.core.repositories.sqlite_gacha_repo import (
    SqliteGachaRepository,
)
from astrbot_plugin_fishing.core.repositories.sqlite_inventory_repo import (
    SqliteInventoryRepository,
)
from astrbot_plugin_fishing.core.repositories.sqlite_item_template_repo import (
    SqliteItemTemplateRepository,
)
from astrbot_plugin_fishing.core.repositories.sqlite_shop_repo import (
    SqliteShopRepository,
)
from astrbot_plugin_fishing.core.services.data_setup_service import (
    DataSetupService,
)


def test_fresh_database_bootstraps_complete_playable_catalog(tmp_path):
    database = tmp_path / "fish.db"
    migrations = (
        Path(__file__).resolve().parents[1]
        / "core"
        / "database"
        / "migrations"
    )
    run_migrations(str(database), str(migrations))

    item_repo = SqliteItemTemplateRepository(str(database))
    gacha_repo = SqliteGachaRepository(str(database))
    shop_repo = SqliteShopRepository(str(database))
    inventory_repo = SqliteInventoryRepository(str(database))
    setup = DataSetupService(
        item_repo, gacha_repo, shop_repo, inventory_repo
    )
    setup.setup_initial_data()
    setup.setup_initial_data()

    connection = sqlite3.connect(database)
    user_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(users)")
    }
    assert "exchange_capacity" in user_columns
    assert connection.execute("SELECT version FROM schema_version").fetchone()[0] == 47
    assert connection.execute("SELECT COUNT(*) FROM fish").fetchone()[0] > 100
    assert connection.execute("SELECT COUNT(*) FROM baits").fetchone()[0] == 14
    assert connection.execute("SELECT COUNT(*) FROM rods").fetchone()[0] == 6
    assert connection.execute(
        "SELECT COUNT(*) FROM accessories"
    ).fetchone()[0] == 7
    assert connection.execute(
        "SELECT COUNT(*) FROM gacha_pool_items"
    ).fetchone()[0] > 0
    for zone_id in range(1, 5):
        assert connection.execute(
            "SELECT COUNT(*) FROM zone_fish_mapping WHERE zone_id = ?",
            (zone_id,),
        ).fetchone()[0] > 0
    connection.close()

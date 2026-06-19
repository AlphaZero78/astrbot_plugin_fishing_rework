from __future__ import annotations

import sqlite3
import time

from astrbot_plugin_fishing.core.services.fishing_service import FishingService


class _Repo:
    def __init__(self, db_path=None):
        self.db_path = str(db_path) if db_path is not None else None


def _service(database):
    return FishingService(
        user_repo=_Repo(database),
        inventory_repo=_Repo(),
        item_template_repo=_Repo(),
        log_repo=_Repo(),
        buff_repo=_Repo(),
        fishing_zone_service=None,
        config={},
    )


def test_shared_runtime_lock_allows_only_one_owner_and_supports_takeover(
    tmp_path,
):
    database = tmp_path / "fish.db"
    sqlite3.connect(database).close()
    first = _service(database)
    second = _service(database)

    assert first._acquire_runtime_lock("auto_fishing_loop", 120) is True
    assert second._acquire_runtime_lock("auto_fishing_loop", 120) is False
    assert first._acquire_runtime_lock("auto_fishing_loop", 120) is True

    first._release_runtime_lock("auto_fishing_loop")
    assert second._acquire_runtime_lock("auto_fishing_loop", 120) is True

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE runtime_locks SET expires_at = ? WHERE lock_name = ?",
            (time.time() - 1, "auto_fishing_loop"),
        )
    assert first._acquire_runtime_lock("auto_fishing_loop", 120) is True

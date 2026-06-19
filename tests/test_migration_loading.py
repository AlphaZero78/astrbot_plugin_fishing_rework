from __future__ import annotations

import sqlite3

from astrbot_plugin_fishing.core.database.migration import load_migration_module


def test_migration_loader_does_not_depend_on_plugin_package_name(tmp_path):
    migration = tmp_path / "999_example.py"
    migration.write_text(
        "def up(cursor):\n"
        "    cursor.execute('CREATE TABLE loaded_from_file (id INTEGER)')\n",
        encoding="utf-8",
    )

    module = load_migration_module(str(tmp_path), migration.name)
    connection = sqlite3.connect(":memory:")
    module.up(connection.cursor())

    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE name = 'loaded_from_file'"
    ).fetchone()
    assert row == ("loaded_from_file",)

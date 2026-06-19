import sqlite3


def _add_column_if_missing(
    cursor: sqlite3.Cursor, table: str, definition: str
) -> None:
    column = definition.split()[0]
    columns = {
        row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def up(cursor: sqlite3.Cursor):
    _add_column_if_missing(cursor, "user_fish_inventory", "unit_value REAL")
    _add_column_if_missing(cursor, "user_aquarium", "unit_value REAL")
    _add_column_if_missing(cursor, "market", "unit_value REAL")

    cursor.execute(
        """
        UPDATE user_fish_inventory
        SET unit_value = (
            SELECT base_value FROM fish
            WHERE fish.fish_id = user_fish_inventory.fish_id
        )
        WHERE unit_value IS NULL
        """
    )
    cursor.execute(
        """
        UPDATE user_aquarium
        SET unit_value = (
            SELECT base_value FROM fish
            WHERE fish.fish_id = user_aquarium.fish_id
        )
        WHERE unit_value IS NULL
        """
    )

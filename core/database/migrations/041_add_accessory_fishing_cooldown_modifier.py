import sqlite3

from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """Add structured fishing cooldown modifier support for accessories."""
    logger.info("Applying 041_add_accessory_fishing_cooldown_modifier...")
    cursor.execute("PRAGMA table_info(accessories)")
    columns = {row[1] for row in cursor.fetchall()}
    if "fishing_cooldown_modifier" not in columns:
        cursor.execute(
            """
            ALTER TABLE accessories
            ADD COLUMN fishing_cooldown_modifier REAL DEFAULT 1.0
            """
        )
    cursor.execute(
        """
        UPDATE accessories
        SET fishing_cooldown_modifier = 1.0
        WHERE fishing_cooldown_modifier IS NULL
        """
    )

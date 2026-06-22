import sqlite3

from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """Add per-user exchange inventory capacity."""
    logger.info("Applying 047_add_exchange_capacity...")
    cursor.execute("PRAGMA table_info(users)")
    columns = {row[1] for row in cursor.fetchall()}
    if "exchange_capacity" not in columns:
        cursor.execute(
            """
            ALTER TABLE users
            ADD COLUMN exchange_capacity INTEGER DEFAULT 1000
            """
        )
    cursor.execute(
        """
        UPDATE users
        SET exchange_capacity = 1000
        WHERE exchange_capacity IS NULL OR exchange_capacity < 1
        """
    )

import json
import sqlite3


ZONE_FIVE_DISTRIBUTION = [0.05, 0.10, 0.15, 0.25, 0.3075, 0.1425]


def up(cursor: sqlite3.Cursor):
    """Keep zone five's baseline gross return near 8x its fishing cost."""
    row = cursor.execute(
        "SELECT configs FROM fishing_zones WHERE id = 5"
    ).fetchone()
    if row is None:
        return

    try:
        config = json.loads(row[0] or "{}")
    except (TypeError, json.JSONDecodeError):
        config = {}
    config["rarity_distribution"] = ZONE_FIVE_DISTRIBUTION
    cursor.execute(
        "UPDATE fishing_zones SET configs = ? WHERE id = 5",
        (json.dumps(config, ensure_ascii=False),),
    )

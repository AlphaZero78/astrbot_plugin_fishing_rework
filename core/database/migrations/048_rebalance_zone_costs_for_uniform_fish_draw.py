import sqlite3


ZONE_COSTS = {
    1: 5,
    2: 25,
    3: 300,
    4: 620,
}


def up(cursor: sqlite3.Cursor):
    """Keep baseline zone returns near 7x after uniform fish selection."""
    for zone_id, cost in ZONE_COSTS.items():
        cursor.execute(
            "UPDATE fishing_zones SET fishing_cost = ? WHERE id = ?",
            (cost, zone_id),
        )

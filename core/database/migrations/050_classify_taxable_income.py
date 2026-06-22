import sqlite3


def up(cursor: sqlite3.Cursor):
    """Separate gross coin credits from the amount taxable as earned profit."""
    columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(income_records)")
    }
    if "taxable_amount" not in columns:
        cursor.execute(
            """
            ALTER TABLE income_records
            ADD COLUMN taxable_amount INTEGER NOT NULL DEFAULT 0
            """
        )

    # Old trigger rows have no trustworthy business source. Exempt the
    # transition period instead of charging transfers or returned principal.
    cursor.execute(
        """
        UPDATE income_records
        SET taxable_amount = 0
        WHERE taxable_amount IS NULL
        """
    )
    cursor.execute("DROP TRIGGER IF EXISTS trg_users_positive_coin_income")
    cursor.execute(
        """
        CREATE TRIGGER trg_users_positive_coin_income
        AFTER UPDATE OF coins ON users
        WHEN NEW.coins > OLD.coins
        BEGIN
            INSERT INTO income_records (
                user_id, amount, taxable_amount, balance_after, source, timestamp
            )
            VALUES (
                NEW.user_id,
                NEW.coins - OLD.coins,
                NEW.coins - OLD.coins,
                NEW.coins,
                '余额正向变动',
                strftime('%Y-%m-%d %H:%M:%f', 'now', '+8 hours') || '+08:00'
            );
        END
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_income_records_taxable_time
        ON income_records(timestamp, taxable_amount)
        """
    )


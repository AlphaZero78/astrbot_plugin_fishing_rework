import sqlite3


def up(cursor: sqlite3.Cursor):
    """Record every positive coin balance change for daily income taxation."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS income_records (
            income_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            amount INTEGER NOT NULL CHECK (amount > 0),
            balance_after INTEGER NOT NULL,
            source TEXT NOT NULL DEFAULT '余额正向变动',
            timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_income_records_user_time
        ON income_records(user_id, timestamp)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_income_records_time
        ON income_records(timestamp)
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
                user_id, amount, balance_after, source, timestamp
            )
            VALUES (
                NEW.user_id,
                NEW.coins - OLD.coins,
                NEW.coins,
                '余额正向变动',
                strftime('%Y-%m-%d %H:%M:%f', 'now', '+8 hours') || '+08:00'
            );
        END
        """
    )

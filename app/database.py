import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent /"data" / "crm.db" 

def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            order_id TEXT NOT NULL UNIQUE,

            created_at TEXT NOT NULL,
            client_id TEXT NOT NULL,
            manager TEXT NOT NULL,

            status_group TEXT NOT NULL
            CHECK (
            status_group IN (
            'new',
            'in_progress',
            'complete',
            'cancel'
                )
            ),
            

            revenue REAL NOT NULL
                CHECK (revenue >= 0),

            cost REAL NOT NULL
                CHECK (cost >= 0),

            source TEXT,
            city TEXT
            )
            """
        )
        
        connection.commit()

if __name__ == "__main__":
    init_db()
    print(f"База данных создана в: {DB_PATH}")
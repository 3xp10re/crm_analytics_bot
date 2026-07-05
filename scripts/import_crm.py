import csv
from pathlib import Path

from app.database import get_connection, init_db

ALLOWED_STATUSES = {
    "new",
    "in_progress",
    "complete",
    "cancel",
}

def import_csv(file_path: str) -> int:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    
    init_db()

    imported_count = 0

    with path.open(mode="r", encoding="utf-8-sig", newline="") as csv_file:

        reader = csv.DictReader(csv_file)

        with get_connection() as connection:
            for row_number, row in enumerate(reader, start=2):
                try:
                    status = row["status_group"].strip()
                    
                    if status not in ALLOWED_STATUSES:
                        raise ValueError(f"неизвестный статус: {status}")
                    
                    revenue = float(row["revenue"])
                    cost = float(row["cost"])

                    connection.execute(
                        """
                        INSERT INTO orders (
                            order_id,
                            created_at,
                            client_id,
                            manager,
                            status_group,
                            revenue,
                            cost,
                            source,
                            city
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

                        ON CONFLICT(order_id) DO UPDATE SET
                            created_at = excluded.created_at,
                            client_id = excluded.client_id,
                            manager = excluded.manager,
                            status_group = excluded.status_group,
                            revenue = excluded.revenue,
                            cost = excluded.cost,
                            source = excluded.source,
                            city = excluded.city
                        """,
                        (
                            row["order_id"].strip(),
                            row["created_at"].strip(),
                            row["client_id"].strip(),
                            row["manager"].strip(),
                            status,
                            revenue,
                            cost,
                            row["source"].strip() or None,
                            row["city"].strip() or None,
                        )
                    )

                    imported_count += 1

                except (KeyError, ValueError) as error:
                    raise ValueError(f"Ошибка в строке {row_number}: {error}") from error
                
            connection.commit()
    return imported_count

if __name__ == "__main__":
    count = import_csv("crm_export.csv")

    print(f"Загружено заказов: {count}")
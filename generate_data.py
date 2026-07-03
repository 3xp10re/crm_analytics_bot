import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "crm_export.csv"

ORDER_COUNT = 1000

MANAGERS = [
    "Иван Петров",
    "Анна Смирнова",
    "Мария Орлова",
    "Алексей Кузнецов",
    "Елена Волкова",
    "Дмитрий Соколов",
]

STATUSES = [
    "new",
    "in_progress",
    "complete",
    "cancel",
]

SOURCES = [
    "Google",
    "Telegram",
    "Instagram",
    "Website",
    "Referral",
    None,
]

CITIES = [
    "Москва",
    "Санкт-Петербург",
    "Казань",
    "Новосибирск",
    "Екатеринбург",
]

CSV_COLUMNS = [
    "order_id",
    "created_at",
    "client_id",
    "manager",
    "status_group",
    "revenue",
    "cost",
    "source",
    "city",
]

def generate_created_at() -> datetime:
    now = datetime.now()
    days_ago = random.randint(0, 179)
    seconds_ago = random.randint(0, 86399)

    return now - timedelta(days=days_ago, seconds=seconds_ago,)


def generate_order(order_number: int) -> dict:
    created_at = generate_created_at()  

    status = random.choices(
        population=STATUSES,
        weights=[15, 20, 55, 10],
        k=1,
    )[0]

    revenue = random.randint(3000, 80000)
    cost_percent = random.uniform(0.45, 0.85)
    cost = round(revenue * cost_percent, 2)

    client_number = random.randint(1, 400)

    source = random.choices(
        population=SOURCES,
        weights=[25, 20, 15, 20, 15, 5],
        k=1,
    )[0]

    return {
        "order_id": f"ORD-{order_number:05d}",
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "client_id": f"CLIENT-{client_number:04d}",
        "manager": random.choice(MANAGERS),
        "status_group": status,
        "revenue": revenue,
        "cost": cost,
        "source": source or "",
        "city": random.choice(CITIES),
    }


def generate_csv(order_count: int = ORDER_COUNT) -> None:
    random.seed(1)
    
    with CSV_PATH.open(
        mode="w",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS,)
        writer.writeheader()

        for order_number in range(1, order_count + 1):
            order = generate_order(order_number)
            writer.writerow(order)
            
    print(f"Создан файл: {CSV_PATH}")
    print(f"Количество заказов: {order_count}")

if __name__ == "__main__":
    generate_csv()
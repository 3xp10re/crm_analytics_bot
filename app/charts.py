import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path

import matplotlib
import matplotlib.dates as mdates  
import matplotlib.pyplot as plt

from app.database import get_connection


matplotlib.use("Agg")

BASE_DIR = Path(__file__).resolve().parent
CHARTS_DIR = BASE_DIR / "data" / "charts"


def get_revenue_by_day(days: int = 30) -> list[dict]:
    today = date.today()
    start_day = today - timedelta(days=days - 1)
    end_day = today + timedelta(days=1)

    start_datetime = datetime.combine(
        start_day,
        time.min,
    )
    end_datetime = datetime.combine(
        end_day,
        time.min,
    )

    query = """
        SELECT
            created_at::date AS order_date,
            COUNT(*) AS leads_count,
            COALESCE(SUM(price), 0) AS total_price

        FROM pechi.amocrm_leads

        WHERE created_at >= %s
          AND created_at < %s

        GROUP BY created_at::date
        ORDER BY order_date
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    start_datetime,
                    end_datetime,
                ),
            )
            rows = cursor.fetchall()

    db_data = {
        row["order_date"]: {
            "revenue": float(row["total_price"]),
            "orders_count": row["leads_count"],
        }
        for row in rows
    }

    result = []

    for day_number in range(days):
        current_day = (
            start_day
            + timedelta(days=day_number)
        )

        day_data = db_data.get(
            current_day,
            {
                "revenue": 0.0,
                "orders_count": 0,
            },
        )

        result.append(
            {
                "date": current_day,
                "revenue": day_data["revenue"],
                "orders_count": day_data[
                    "orders_count"
                ],
            }
        )

    return result


def create_revenue_chart(days: int = 30) -> Path | None:
    revenue_data = get_revenue_by_day(days)

    has_orders = any(
        day["orders_count"] > 0
        for day in revenue_data
    )

    if not has_orders:
        return None
    
    dates = [
        day["date"]
        for day in revenue_data
    ]

    revenues = [
        day["revenue"]
        for day in revenue_data
    ]

    CHARTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    chart_path = (
        CHARTS_DIR
        / f"revenue_{uuid.uuid4().hex}.png"
    )

    figure, axes = plt.subplots(
        figsize=(12, 6)
    )

    axes.plot(
        dates,
        revenues,
        marker="o",
        linewidth=2,
    )

    axes.set_title(
        "Выручка по дням за последние 30 дней"
    )

    axes.set_xlabel("Дата")
    axes.set_ylabel("Выручка")
    axes.grid(True, alpha=0.3)

    axes.xaxis.set_major_locator(
        mdates.DayLocator(interval=3)
    )

    axes.xaxis.set_major_formatter(
        mdates.DateFormatter("%d.%m")
    )

    figure.autofmt_xdate()
    figure.tight_layout()

    figure.savefig(
        chart_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(figure)

    return chart_path


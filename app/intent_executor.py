from datetime import date

from app.database import get_connection
from app.schemas import QueryIntent


def validate_period(
    intent: QueryIntent,) -> tuple[str, str]:
    if intent.start_date is None:
        raise ValueError("start_date отсутствует")

    if intent.end_date is None:
        raise ValueError("end_date отсутствует")

    try:
        start_date = date.fromisoformat(
            intent.start_date
        )
        end_date = date.fromisoformat(
            intent.end_date
        )
    except ValueError as error:
        raise ValueError(
            "Некорректный формат даты"
        ) from error

    if start_date >= end_date:
        raise ValueError(
            "start_date должен быть раньше end_date"
        )

    if (end_date - start_date).days > 730:
        raise ValueError(
            "Слишком большой период"
        )

    start_datetime = (
        f"{start_date.isoformat()} 00:00:00"
    )

    end_datetime = (
        f"{end_date.isoformat()} 00:00:00"
    )

    return start_datetime, end_datetime


def format_money(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ")


def execute_intent(intent: QueryIntent,) -> str:
    if intent.intent == "unsupported":
        return (
            "В текущей базе нет данных, "
            "чтобы посчитать этот показатель."
        )
    start_date, end_date = validate_period(intent)

    with get_connection() as connection:
        if intent.intent == "revenue":
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS completed_orders,

                COALESCE(
                        SUM(revenue),
                        0
                    ) AS revenue

                FROM orders
                  WHERE created_at >= ?
                  AND created_at < ?
                  AND status_group = 'complete'
                """,(start_date, end_date,)).fetchone()
            
            if row["completed_orders"] == 0:
                return (
                    "В базе нет завершённых заказов "
                    "за указанный период."
                )
            
            return (
                f"Выручка за период "
                f"с {intent.start_date} "
                f"по {intent.end_date}: "
                f"{format_money(row['revenue'])}.\n"
                f"Завершённых заказов: "
                f"{row['completed_orders']}."
            )
    
        if intent.intent == "cancelled_orders":
            row = connection.execute(
                """
                SELECT
                    COUNT (*) AS cancelled_orders

                FROM orders

                WHERE created_at >= ?
                    AND created_at < ?
                    AND status_group = 'cancel'
                """, (start_date, end_date),).fetchone()
            
            return (
                f"За указанный период отменено "
                f"{row['cancelled_orders']} заказов."
            )
        
        if intent.intent == "best_manager_by_margin":
            row = connection.execute(
                """
                SELECT
                    manager,
                    COUNT(*) AS completed_orders,
                    SUM(revenue) AS revenue,
                    SUM(revenue - cost) AS margin

                FROM orders

                WHERE created_at >= ?
                    AND created_at < ?
                    AND status_group = 'complete'

                GROUP BY manager
                ORDER BY margin DESC
                LIMIT 1
                """, (start_date, end_date)).fetchone()

            if row is None:
                return (
                    "В базе нет данных, чтобы определить "
                    "лучшего менеджера по марже."
                )
            
            return (
                f"Лучший менеджер по марже — "
                f"{row['manager']}.\n"
                f"Маржа: {format_money(row['margin'])}.\n"
                f"Выручка: {format_money(row['revenue'])}.\n"
                f"Завершённых заказов: "
                f"{row['completed_orders']}."
            )
        
        if intent.intent == "top_source_by_orders":
            row = connection.execute(
                """
                SELECT 
                    source,
                    COUNT (*) AS orders_count

                FROM orders

                WHERE created_at >= ?
                  AND created_at < ?
                  AND source IS NOT NULL
                  AND TRIM(source) != ''

                GROUP BY source
                ORDER BY orders_count DESC
                LIMIT 1
                """, (start_date, end_date)).fetchone()
            
            if row is None:
                return (
                    "В базе нет данных об источниках заказов "
                    "за указанный период."
                )

            return (
                f"Больше всего заказов дал источник "
                f"«{row['source']}»: "
                f"{row['orders_count']} заказов."
            )
        
        if intent.intent == "city_highest_average_check":
            row = connection.execute(
                """
                SELECT 
                    city,
                    COUNT (*) AS completed_orders,
                    AVG(revenue) AS average_check

                FROM orders

                WHERE created_at >= ?
                  AND created_at < ?
                  AND status_group = 'complete'
                  AND city IS NOT NULL
                  AND TRIM(city) != ''
                
                GROUP by city
                ORDER by average_check DESC
                LIMIT 1
                """, (start_date, end_date)).fetchone()
            
            if row is None:
                return (
                    "В базе нет данных, чтобы сравнить "
                    "средний чек по городам."
                )

            return (
                f"Самый высокий средний чек "
                f"в городе «{row['city']}»: "
                f"{format_money(row['average_check'])}.\n"
                f"Завершённых заказов: "
                f"{row['completed_orders']}."
            )

    return (
        "В текущей базе нет данных, "
        "чтобы посчитать этот показатель."
    )


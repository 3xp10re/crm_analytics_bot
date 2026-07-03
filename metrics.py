from datetime import datetime
from database import get_connection


def get_current_month_metrics() -> dict:
    start_date, end_date = get_current_month_bounds()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS orders_count,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status_group = 'complete'
                            THEN revenue
                            ELSE 0
                        END
                    ),
                    0
                ) AS revenue,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status_group = 'complete'
                            THEN revenue - cost
                            ELSE 0
                        END
                    ),
                    0
                ) AS margin,

                COALESCE(
                    AVG(
                        CASE
                            WHEN status_group = 'complete'
                            THEN revenue
                        END
                    ),
                    0
                ) AS average_check,

                SUM(
                    CASE
                        WHEN status_group = 'complete'
                        THEN 1
                        ELSE 0
                    END
                ) AS successful_orders,

                SUM(
                    CASE
                        WHEN status_group = 'cancel'
                        THEN 1
                        ELSE 0
                    END
                ) AS cancelled_orders

                FROM orders

                WHERE created_at >= ?
                AND created_at < ?
            """, (start_date, end_date,),).fetchone()
        
        new_clients_row = connection.execute(
            """
            SELECT COUNT(*) AS new_clients
            FROM (
                SELECT client_id
                FROM orders
                GROUP BY client_id

                HAVING MIN(created_at) >= ?
                AND MIN(created_at) < ?
                )
            """, (start_date, end_date,),).fetchone()
        
    orders_count = row["orders_count"]
    cancelled_orders = row["cancelled_orders"]

    if orders_count > 0:
        cancellation_rate = (cancelled_orders / orders_count * 100)
    else:
        cancellation_rate = 0

    return {
        "orders_count": orders_count,
        "revenue": row["revenue"],
        "margin": row["margin"],
        "average_check": row["average_check"],
        "successful_orders": row["successful_orders"],
        "cancelled_orders": cancelled_orders,
        "cancellation_rate": cancellation_rate,
        "new_clients": new_clients_row["new_clients"],
    }
        

def get_current_month_bounds() -> tuple[str, str]:
    now = datetime.now()
    start_date = datetime(
        year=now.year,
        month=now.month,
        day=1,
    )

    if now.month == 12:
        end_date = datetime(
            year=now.year + 1,
            month=1,
            day=1,
        )

    else:
        end_date = datetime(
            year=now.year,
            month=now.month + 1,
            day=1,
        )

    return (
        start_date.strftime("%Y-%m-%d %H:%M:%S"),
        end_date.strftime("%Y-%m-%d %H:%M:%S"),
    )



if __name__ == "__main__":
    metrics = get_current_month_metrics()

    print("Метрики за текущий месяц")
    print("------------------------")
    print(f"Количество заказов: {metrics['orders_count']}")
    print(f"Выручка: {metrics['revenue']:.2f}")
    print(f"Маржа: {metrics['margin']:.2f}")
    print(f"Средний чек: {metrics['average_check']:.2f}")
    print(f"Успешных заказов: {metrics['successful_orders']}")
    print(f"Отменённых заказов: {metrics['cancelled_orders']}")
    print(f"Доля отмен: {metrics['cancellation_rate']:.2f}%")
    print(f"Новых клиентов: {metrics['new_clients']}")
        
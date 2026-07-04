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
        

def get_top_managers() -> list[dict]:
    start_date, end_date = get_current_month_bounds()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                manager,

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

                COALESCE(
                    100.0 * SUM(
                        CASE
                            WHEN status_group = 'complete'
                            THEN 1
                            ELSE 0
                        END
                    ) / COUNT(*),
                    0
                ) AS success_rate

            FROM orders
            WHERE created_at >= ?
            AND created_at < ?

            GROUP BY manager
            ORDER BY revenue DESC, margin DESC
            LIMIT 5

            """, (start_date, end_date),).fetchall()
    return [dict(row) for row in rows]


def get_status_report() -> list[dict]:
    start_date, end_date = get_current_month_bounds()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT status_group, 

            COUNT(*) as orders_count

            FROM orders

            WHERE created_at >= ?
                AND created_at < ?

            GROUP BY status_group
            """, (start_date, end_date,)).fetchall()
    return [dict(row) for row in rows]


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

        
from datetime import datetime
from app.database import get_connection


def get_current_month_metrics() -> dict:
    start_date, end_date = get_current_month_bounds()

    query = """
            SELECT 
                COUNT(*) AS leads_count,

                COALESCE(SUM(price), 0) AS total_price,

                COALESCE(AVG(price), 0) AS average_price,

                COUNT(DISTINCT responsible_user_id) AS managers_count,

                COUNT(*) FILTER (WHERE responsible_user_id IS NULL) AS leads_without_manager,

                COUNT(*) FILTER (WHERE source IS NULL OR BTRIM(source) = '') AS leads_without_source,

                COUNT(*) FILTER (WHERE product_category IS NULL OR BTRIM(product_category) = '') AS leads_without_category

                FROM pechi.amocrm_leads

                WHERE created_at >= %s
                AND created_at < %s
            """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (start_date, end_date),)

            row = cursor.fetchone()

        return dict(row)  
        

def get_top_managers() -> list[dict]:
    start_date, end_date = get_current_month_bounds()

    query = """
            SELECT
            COALESCE(
                NULLIF(BTRIM(l.responsible_manager), ''),
                u.name,
                l.responsible_user_id::text,
                'Не назначен'
            ) AS manager,

            COUNT(*) AS leads_count, 

            COALESCE(SUM(l.price), 0) AS total_price,

            COALESCE(AVG(l.price), 0) AS average_price

            FROM pechi.amocrm_leads AS l

            LEFT JOIN pechi.amocrm_users AS u
            ON u.id = l.responsible_user_id

        WHERE l.created_at >= %s
          AND l.created_at < %s

        GROUP BY
            l.responsible_manager,
            l.responsible_user_id,
            u.id,
            u.name

        ORDER BY
            leads_count DESC,
            total_price DESC

        LIMIT 5
            """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (start_date, end_date),
            )

            rows = cursor.fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_status_report() -> list[dict]:
    start_date, end_date = get_current_month_bounds()

    query = """
        SELECT
            COALESCE(
                p.name,
                'Неизвестная воронка'
            ) AS pipeline_name,

            COALESCE(
                s.name,
                'Неизвестный статус'
            ) AS status_name,

            COUNT(*) AS leads_count,

            COALESCE(
                SUM(l.price),
                0
            ) AS total_price

        FROM pechi.amocrm_leads AS l

        LEFT JOIN pechi.amocrm_statuses AS s
            ON s.id = l.status_id

        LEFT JOIN pechi.amocrm_pipelines AS p
            ON p.id = l.pipeline_id

        WHERE l.created_at >= %s
          AND l.created_at < %s

        GROUP BY
            p.id,
            p.name,
            s.id,
            s.name

        ORDER BY
            pipeline_name,
            leads_count DESC
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (start_date, end_date),
            )

            rows = cursor.fetchall()

    return [
        dict(row)
        for row in rows
    ]


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

        
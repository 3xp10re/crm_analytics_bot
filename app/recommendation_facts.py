from datetime import datetime, timedelta

from app.database import get_connection
from app.intent_executor import format_money
from app.metrics import get_current_month_bounds
from app.schemas import RecommendationFact


def collect_recommendation_facts() -> list[RecommendationFact]:
    start_date, end_date = get_current_month_bounds()

    facts: list[RecommendationFact] = []

    stale_date = datetime.now() - timedelta(days=7)
    stale_date_str = stale_date.strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as connection:
        manager_row = connection.execute(
            """
            SELECT
                manager,
                COUNT(*) AS orders_count,

                SUM(
                    CASE
                        WHEN status_group = 'cancel'
                        THEN 1
                        ELSE 0
                    END
                ) AS cancelled_orders,

                100.0 * SUM(
                    CASE
                        WHEN status_group = 'cancel'
                        THEN 1
                        ELSE 0
                    END
                ) / COUNT(*) AS cancellation_rate

            FROM orders

            WHERE created_at >= ?
              AND created_at < ?

            GROUP BY manager

            HAVING COUNT(*) >= 3

            ORDER BY cancellation_rate DESC

            LIMIT 1
            """,
            (
                start_date,
                end_date,
            ),
        ).fetchone()

        source_row = connection.execute(
            """
            SELECT
                source,
                COUNT(*) AS completed_orders,
                SUM(revenue) AS revenue,
                SUM(revenue - cost) AS margin,

                100.0 * SUM(revenue - cost)
                    / SUM(revenue) AS margin_rate

            FROM orders

            WHERE created_at >= ?
              AND created_at < ?
              AND status_group = 'complete'
              AND source IS NOT NULL
              AND TRIM(source) != ''

            GROUP BY source

            HAVING COUNT(*) >= 3
               AND SUM(revenue) > 0

            ORDER BY margin_rate ASC

            LIMIT 1
            """,
            (
                start_date,
                end_date,
            ),
        ).fetchone()

        stale_orders_row = connection.execute(
            """
            SELECT
                COUNT(*) AS orders_count,
                MIN(created_at) AS oldest_created_at

            FROM orders

            WHERE status_group = 'new'
              AND created_at < ?
            """,
            (
                stale_date_str,
            ),
        ).fetchone()

        missing_source_row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_orders,

                SUM(
                    CASE
                        WHEN source IS NULL
                          OR TRIM(source) = ''
                        THEN 1
                        ELSE 0
                    END
                ) AS missing_source_orders

            FROM orders

            WHERE created_at >= ?
              AND created_at < ?
            """,
            (
                start_date,
                end_date,
            ),
        ).fetchone()

        city_row = connection.execute(
            """
            SELECT
                city,
                COUNT(*) AS completed_orders,
                AVG(revenue) AS average_check

            FROM orders

            WHERE created_at >= ?
              AND created_at < ?
              AND status_group = 'complete'
              AND city IS NOT NULL
              AND TRIM(city) != ''

            GROUP BY city

            HAVING COUNT(*) >= 3

            ORDER BY average_check ASC

            LIMIT 1
            """,
            (
                start_date,
                end_date,
            ),
        ).fetchone()

    if manager_row is not None:
        cancelled_orders = manager_row["cancelled_orders"] or 0
        cancellation_rate = float(
            manager_row["cancellation_rate"] or 0
        )

        if cancelled_orders > 0:
            facts.append(
                RecommendationFact(
                    id="high_manager_cancellation",
                    category="manager",
                    priority=cancellation_rate,
                    evidence={
                        "manager": manager_row["manager"],
                        "orders_count": manager_row["orders_count"],
                        "cancelled_orders": cancelled_orders,
                        "cancellation_rate": round(
                            cancellation_rate,
                            1,
                        ),
                    },
                    text=(
                        f"Проверить менеджера "
                        f"«{manager_row['manager']}»: "
                        f"доля отмен за текущий месяц составляет "
                        f"{cancellation_rate:.1f}% "
                        f"({cancelled_orders} из "
                        f"{manager_row['orders_count']} заказов)."
                    ),
                )
            )

    if source_row is not None:
        margin_rate = float(source_row["margin_rate"] or 0)
        revenue = float(source_row["revenue"] or 0)
        margin = float(source_row["margin"] or 0)

        facts.append(
            RecommendationFact(
                id="low_source_margin",
                category="source",
                priority=100 - margin_rate,
                evidence={
                    "source": source_row["source"],
                    "completed_orders": source_row[
                        "completed_orders"
                    ],
                    "revenue": round(
                        revenue,
                        2,
                    ),
                    "margin": round(
                        margin,
                        2,
                    ),
                    "margin_rate": round(
                        margin_rate,
                        1,
                    ),
                },
                text=(
                    f"Обратить внимание на источник "
                    f"«{source_row['source']}»: "
                    f"маржинальность составляет "
                    f"{margin_rate:.1f}%. "
                    f"Выручка — {format_money(revenue)}, "
                    f"маржа — {format_money(margin)}."
                ),
            )
        )

    if stale_orders_row is not None:
        stale_orders_count = stale_orders_row["orders_count"] or 0

        if stale_orders_count > 0:
            facts.append(
                RecommendationFact(
                    id="stale_new_orders",
                    category="orders",
                    priority=float(stale_orders_count),
                    evidence={
                        "orders_count": stale_orders_count,
                        "oldest_created_at": stale_orders_row[
                            "oldest_created_at"
                        ],
                        "days_in_new": 7,
                    },
                    text=(
                        f"Проверить {stale_orders_count} заказов, "
                        f"которые были созданы более 7 дней назад "
                        f"и всё ещё находятся в статусе new. "
                        f"Самый старый из них создан: "
                        f"{stale_orders_row['oldest_created_at']}."
                    ),
                )
            )

    if missing_source_row is not None:
        total_orders = missing_source_row["total_orders"] or 0
        missing_orders = (
            missing_source_row["missing_source_orders"] or 0
        )

        if total_orders > 0 and missing_orders > 0:
            missing_rate = missing_orders / total_orders * 100

            facts.append(
                RecommendationFact(
                    id="missing_sources",
                    category="data_quality",
                    priority=missing_rate,
                    evidence={
                        "missing_orders": missing_orders,
                        "total_orders": total_orders,
                        "missing_rate": round(
                            missing_rate,
                            1,
                        ),
                    },
                    text=(
                        f"У {missing_orders} из {total_orders} "
                        f"заказов текущего месяца не указан "
                        f"источник ({missing_rate:.1f}%). "
                    ),
                )
            )

    if city_row is not None:
        average_check = float(city_row["average_check"] or 0)

        facts.append(
            RecommendationFact(
                id="low_city_average_check",
                category="city",
                priority=1,
                evidence={
                    "city": city_row["city"],
                    "completed_orders": city_row[
                        "completed_orders"
                    ],
                    "average_check": round(
                        average_check,
                        2,
                    ),
                },
                text=(
                    f"Изучить продажи в городе "
                    f"«{city_row['city']}»: "
                    f"самый низкий средний чек среди городов "
                    f"с минимум тремя завершёнными заказами — "
                    f"{format_money(average_check)}."
                ),
            )
        )

    return facts
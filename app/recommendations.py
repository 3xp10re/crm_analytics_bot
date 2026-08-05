import asyncio
import json
import logging
from typing import Any

from app.database import get_connection
from app.llm_client import chat_with_ollama


logger = logging.getLogger(__name__)

RECOMMENDATION_PERIOD_DAYS = 30

def get_recommendation_data(period_days: int = RECOMMENDATION_PERIOD_DAYS,) -> dict[str, Any]:

    with get_connection() as connection:
        with connection.cursor() as cursor:

            # Общие показатели
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS leads_count,

                    COALESCE(
                        SUM(price),
                        0
                    ) AS total_price,

                    COALESCE(
                        AVG(price),
                        0
                    ) AS average_price,

                    COUNT(*) FILTER (
                        WHERE responsible_user_id IS NULL
                    ) AS unassigned_leads,

                    COUNT(*) FILTER (
                        WHERE source IS NULL
                           OR BTRIM(source) = ''
                    ) AS leads_without_source

                FROM pechi.amocrm_leads

                WHERE created_at >= (
                    CURRENT_TIMESTAMP
                    - (%s * INTERVAL '1 day')
                );
                """,
                (period_days,),
            )

            overview = cursor.fetchone()

            # Распределение сделок по менеджерам
            cursor.execute(
                """
                SELECT
                    COALESCE(
                        u.name,
                        'Менеджер не назначен'
                    ) AS manager_name,

                    COUNT(*) AS leads_count,

                    COALESCE(
                        SUM(l.price),
                        0
                    ) AS total_price

                FROM pechi.amocrm_leads AS l

                LEFT JOIN pechi.amocrm_users AS u
                    ON u.id = l.responsible_user_id

                WHERE l.created_at >= (
                    CURRENT_TIMESTAMP
                    - (%s * INTERVAL '1 day')
                )

                GROUP BY
                    u.id,
                    u.name

                ORDER BY
                    leads_count DESC

                LIMIT 5;
                """,
                (period_days,),
            )

            managers = cursor.fetchall()

            # Распределение по статусам
            cursor.execute(
                """
                SELECT
                    COALESCE(
                        s.name,
                        'Статус не указан'
                    ) AS status_name,

                    COUNT(*) AS leads_count,

                    COALESCE(
                        SUM(l.price),
                        0
                    ) AS total_price

                FROM pechi.amocrm_leads AS l

                LEFT JOIN pechi.amocrm_statuses AS s
                    ON s.id = l.status_id

                WHERE l.created_at >= (
                    CURRENT_TIMESTAMP
                    - (%s * INTERVAL '1 day')
                )

                GROUP BY
                    s.id,
                    s.name

                ORDER BY
                    leads_count DESC

                LIMIT 10;
                """,
                (period_days,),
            )

            statuses = cursor.fetchall()

            # Основные источники
            cursor.execute(
                """
                SELECT
                    COALESCE(
                        NULLIF(BTRIM(source), ''),
                        'Источник не указан'
                    ) AS source_name,

                    COUNT(*) AS leads_count,

                    COALESCE(
                        SUM(price),
                        0
                    ) AS total_price

                FROM pechi.amocrm_leads

                WHERE created_at >= (
                    CURRENT_TIMESTAMP
                    - (%s * INTERVAL '1 day')
                )

                GROUP BY
                    COALESCE(
                        NULLIF(BTRIM(source), ''),
                        'Источник не указан'
                    )

                ORDER BY
                    leads_count DESC

                LIMIT 10;
                """,
                (period_days,),
            )

            sources = cursor.fetchall()

    return {
        "period_days": period_days,
        "overview": overview,
        "managers": managers,
        "statuses": statuses,
        "sources": sources,
    }


async def generate_recommendations(
    period_days: int = RECOMMENDATION_PERIOD_DAYS,
) -> str:
    logger.info(
        "Формирование рекомендаций за последние %d дней",
        period_days,
    )

    data = await asyncio.to_thread(
        get_recommendation_data,
        period_days,
    )

    logger.info(
        "Данные для рекомендаций: %r",
        data,
    )

    overview = data.get("overview")

    if not overview or overview.get("leads_count", 0) == 0:
        return (
            f"За последние {period_days} дней "
            "недостаточно данных для формирования рекомендаций."
        )

    result_json = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    system_prompt = """
Ты CRM-аналитик.

На основании переданных показателей сформируй
от 3 до 5 практических рекомендаций.

Правила:

1. Отвечай только на русском языке.
2. Используй исключительно переданные данные.
3. Не придумывай причины, события и показатели.
4. Каждая рекомендация должна содержать:
   - конкретный факт или число;
   - понятное действие.
5. Сначала показывай наиболее важные проблемы.
6. Обращай внимание на:
   - сделки без назначенного менеджера;
   - сделки без указанного источника;
   - сильную концентрацию сделок у одного менеджера;
   - распределение по статусам;
   - эффективность источников.
7. Не называй обычные сделки завершёнными продажами,
   если в данных нет подтверждения успешного статуса.
8. Не утверждай, что один источник эффективнее другого
   только по количеству сделок.
9. Не делай вывод о прибыльности,
   если нет данных о расходах и марже.
10. Не упоминай SQL, JSON, таблицы, базу данных
    и внутреннее устройство программы.
11. Оформи ответ нумерованным списком.
12. Пиши коротко и конкретно.
""".strip()

    user_prompt = f"""
Период анализа: последние {period_days} дней.

ПОКАЗАТЕЛИ CRM:

{result_json}

Сформируй практические рекомендации.
""".strip()

    try:
        recommendations = await chat_with_ollama(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )

        logger.info(
            "Сформированные рекомендации: %s",
            recommendations,
        )

        return recommendations

    except RuntimeError:
        logger.exception(
            "Не удалось сформировать рекомендации через Ollama"
        )

        return build_fallback_recommendations(data)


def build_fallback_recommendations(data: dict[str, Any],) -> str:

    overview = data["overview"]
    managers = data["managers"]
    statuses = data["statuses"]
    period_days = data["period_days"]

    leads_count = overview["leads_count"]
    unassigned_leads = overview["unassigned_leads"]
    leads_without_source = overview["leads_without_source"]

    recommendations: list[str] = []

    if unassigned_leads > 0:
        share = unassigned_leads / leads_count * 100

        recommendations.append(
            f"Назначьте ответственных для {unassigned_leads} "
            f"сделок ({share:.1f}% от общего количества), "
            "чтобы они не оставались без контроля."
        )

    if leads_without_source > 0:
        share = leads_without_source / leads_count * 100

        recommendations.append(
            f"Заполните источник у {leads_without_source} "
            f"сделок ({share:.1f}%), иначе оценить каналы "
            "привлечения будет невозможно."
        )

    if managers:
        top_manager = managers[0]
        top_manager_leads = top_manager["leads_count"]
        manager_share = top_manager_leads / leads_count * 100

        if manager_share >= 40:
            recommendations.append(
                f"На менеджера «{top_manager['manager_name']}» "
                f"приходится {top_manager_leads} сделок "
                f"({manager_share:.1f}%). Проверьте равномерность "
                "распределения нагрузки между менеджерами."
            )

    if statuses:
        largest_status = statuses[0]

        recommendations.append(
            f"Больше всего сделок находится в статусе "
            f"«{largest_status['status_name']}» — "
            f"{largest_status['leads_count']}. Проверьте, "
            "не задерживаются ли сделки на этом этапе."
        )

    if not recommendations:
        recommendations.append(
            "Критических отклонений в основных показателях "
            "не обнаружено. Продолжайте отслеживать распределение "
            "сделок по менеджерам, статусам и источникам."
        )

    numbered_recommendations = "\n".join(
        f"{number}. {recommendation}"
        for number, recommendation in enumerate(
            recommendations[:5],
            start=1,
        )
    )

    return (
        f"Рекомендации за последние {period_days} дней:\n\n"
        f"{numbered_recommendations}"
    )
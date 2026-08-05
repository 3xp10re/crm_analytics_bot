import asyncio
import logging

from app.database_schema import get_database_schema
from app.llm_client import (
    correct_sql,
    generate_answer,
    generate_sql,
)
from app.sql_executor import execute_sql
from app.sql_validator import validate_sql


logger = logging.getLogger(__name__)

MAX_SQL_ATTEMPTS = 2


async def process_query(question: str) -> str:
    logger.info("Вопрос пользователя: %s", question)

    schema = await asyncio.to_thread(get_database_schema)

    current_sql = await generate_sql(question=question,database_schema=schema,)

    logger.info("Сформированный SQL: %s", current_sql)

    sql_result: list[dict] | None = None
    last_error: Exception | None = None

    for attempt in range(MAX_SQL_ATTEMPTS):
        try:
            logger.info(
                "Выполнение SQL, попытка %d из %d: %s",
                attempt + 1,
                MAX_SQL_ATTEMPTS,
                current_sql,
            )

            validated_sql = validate_sql(current_sql)

            sql_result = await asyncio.to_thread(execute_sql,validated_sql,)

            logger.info("Результат выполнения SQL: %r", sql_result,)

            break

        except Exception as error:
            last_error = error

            logger.warning(
                "Ошибка SQL на попытке %d из %d. SQL: %s. Ошибка: %s",
                attempt + 1,
                MAX_SQL_ATTEMPTS,
                current_sql,
                error,
            )

            if attempt == MAX_SQL_ATTEMPTS - 1:
                logger.exception(
                    "Не удалось сформировать корректный SQL "
                   "после %d попыток",
                    MAX_SQL_ATTEMPTS,
                )

                raise RuntimeError(
                    "Не удалось сформировать корректный "
                    "SQL-запрос."
                ) from error

            current_sql = await correct_sql(
                question=question,
                database_schema=schema,
                incorrect_sql=current_sql,
                error_message=str(error),
            )

            logger.info(
                "Исправленный SQL: %s",
                current_sql,
            )

    if sql_result is None:
        logger.error(
            "SQL-запрос не вернул результат. Последняя ошибка: %r",
            last_error,
        )
        
        raise RuntimeError(
            "SQL-запрос не вернул результат."
        ) from last_error

    answer = await generate_answer(
        question=question,
        sql_result=sql_result,
    )

    return answer
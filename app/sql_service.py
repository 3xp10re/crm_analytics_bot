import asyncio

from app.database_schema import get_database_schema
from app.llm_client import (
    correct_sql,
    generate_answer,
    generate_sql,
)
from app.sql_executor import execute_sql
from app.sql_validator import validate_sql


MAX_SQL_ATTEMPTS = 2


async def process_query(question: str) -> str:
    schema = await asyncio.to_thread(get_database_schema)

    current_sql = await generate_sql(question=question,database_schema=schema,)

    sql_result: list[dict] | None = None
    last_error: Exception | None = None

    for attempt in range(MAX_SQL_ATTEMPTS):
        try:
            validated_sql = validate_sql(current_sql)

            sql_result = await asyncio.to_thread(execute_sql,validated_sql,)

            break

        except Exception as error:
            last_error = error

            print(f"Ошибка SQL, попытка {attempt + 1}:", repr(error),)

            if attempt == MAX_SQL_ATTEMPTS - 1:
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

            print("Исправленный SQL:")
            print(current_sql)

    if sql_result is None:
        raise RuntimeError(
            "SQL-запрос не вернул результат."
        ) from last_error

    answer = await generate_answer(
        question=question,
        sql_result=sql_result,
    )

    return answer
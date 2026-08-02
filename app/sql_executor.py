from typing import Any
from psycopg import errors

from app.database import get_connection


MAX_ROWS = 100
STATEMENT_TIMEOUT_MS = 5000


class SQLExecutionError(Exception):
    pass


def execute_sql(sql: str) -> list[dict]:
    try:
        with get_connection() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION READ ONLY")
                    cursor.execute(
                        f"""
                        SET LOCAL statement_timeout =
                        {STATEMENT_TIMEOUT_MS}
                        """
                    )

                    cursor.execute(sql)

                    if cursor.description is None:
                        raise SQLExecutionError(
                            "Запрос не вернул данные."
                        )
                    
                    rows = cursor.fetchmany(MAX_ROWS+1)

                    if len(rows) > MAX_ROWS:
                        rows = rows[:MAX_ROWS]

                    return [
                        dict(row)
                        for row in rows
                    ]

    except errors.QueryCanceled as error:
        raise SQLExecutionError(
            "Превышено время выполнения запроса."
        ) from error

    except SQLExecutionError:
        raise

    except SQLExecutionError:
        raise
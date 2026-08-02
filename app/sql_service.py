import asyncio

from app.llm_client import generate_sql
from app.database_schema import get_database_schema
from app.sql_validator import validate_sql
from app.sql_executor import execute_sql
from app.llm_client import generate_answer


async def process_query(question: str):
    schema = await asyncio.to_thread(get_database_schema)

    query = await generate_sql(question=question, database_schema=schema)

    validated_query = validate_sql(query)

    sql_result = await asyncio.to_thread(execute_sql, validated_query,)

    answer = await generate_answer(question=question, sql_result=sql_result,)

    return answer
from app.llm_client import generate_sql
from app.database_schema import get_database_schema
from app.sql_validator import validate_sql
from app.sql_executor import execute_sql


async def process_query(question: str):
    schema = get_database_schema()

    query = await generate_sql(question=question, database_schema=schema)

    validated_query = validate_sql(query)

    result = execute_sql(validated_query)

    return result
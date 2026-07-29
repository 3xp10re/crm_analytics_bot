import asyncio

from app.database_schema import get_database_schema
from app.llm_client import generate_sql


async def main():
    schema = get_database_schema()

    question = "Покажи пять менеджеров с самым большим количеством сделок."

    sql = await generate_sql(
        question=question,
        database_schema=schema
    )

    print("Вопрос:")
    print(question)

    print()

    print("SQL:")
    print(sql)


if __name__ == "__main__":
    asyncio.run(main())
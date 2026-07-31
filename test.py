import asyncio

from app.sql_service import process_query


async def main():
    result = await process_query(
        "Сколько всего сделок находится в базе?"
    )

    print(result)


asyncio.run(main())
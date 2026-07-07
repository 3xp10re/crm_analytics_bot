from datetime import date
from typing import Literal
import os

import httpx
from pydantic import BaseModel
from dotenv import load_dotenv
import asyncio
from app.database import get_connection
from app.schemas import QueryIntent

load_dotenv()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
OLLAMA_URL = os.getenv("OLLAMA_URL")


async def parse_question_with_llm(question: str,) -> QueryIntent:
    today = date.today().isoformat()

    system_prompt = f"""
Ты анализатор вопросов к CRM-базе.

Текущая дата: {today}.

Таблица orders содержит поля:
- order_id
- created_at
- client_id
- manager
- status_group
- revenue
- cost
- source
- city

Возможные значения status_group:
- new
- in_progress
- complete
- cancel

Поддерживаемые намерения:

1. revenue
Вопрос про выручку за период.
Выручка считается только по заказам со статусом complete.

2. cancelled_orders
Вопрос про количество отменённых заказов за период.
Отменённые заказы имеют status_group = cancel.

3. best_manager_by_margin
Вопрос про лучшего менеджера по марже.
Маржа = revenue - cost.
Учитываются только complete-заказы.

4. top_source_by_orders
Вопрос про источник, который дал больше всего заказов.

5. city_highest_average_check
Вопрос про город с самым высоким средним чеком.
Средний чек считается только по complete-заказам.

6. unsupported
Если вопрос нельзя посчитать по таблице orders.
Например: ROMI, рекламные расходы, налоги, зарплаты.

Правила:
- Верни только JSON.
- Не возвращай SQL.
- Не пиши объяснения.
- Не используй китайский язык.
- Не считай показатели самостоятельно.
- Не придумывай данные.
- start_date включается.
- end_date не включается.
- Формат дат: YYYY-MM-DD.
- Если период не указан, используй текущий месяц.
"""
    
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        "format": QueryIntent.model_json_schema(),
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload,)
        response.raise_for_status()
        data = response.json()
        content = data["message"]["content"]

        return QueryIntent.model_validate_json(content)

import json
import os

import httpx
from dotenv import load_dotenv

from app.schemas import (
    RecommendationFact,
    RecommendationPlan,
)


load_dotenv()


OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
OLLAMA_URL = os.getenv("OLLAMA_URL")


async def select_recommendations_with_llm(facts: list[RecommendationFact],) -> list[str]:
    if not facts:
        return []

    llm_facts = [
        {
            "id": fact.id,
            "category": fact.category,
            "priority": fact.priority,
            "evidence": fact.evidence,
        }
        for fact in facts
    ]

    system_prompt = """
Ты CRM-аналитик.

Тебе переданы факты, которые уже рассчитаны SQL-запросами.

Твоя задача:
- выбрать от 1 до 5 самых важных фактов;
- вернуть только id выбранных фактов;
- не придумывать новые id;
- не придумывать новые числа;
- не писать рекомендации текстом;
- не выполнять расчёты самостоятельно.

Выбирай факты, которые сильнее всего влияют на бизнес:
- высокая доля отмен;
- низкая маржинальность;
- старые заказы без движения;
- проблемы качества данных;
- низкий средний чек.
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
                "content": json.dumps(
                    llm_facts,
                    ensure_ascii=False,
                ),
            },
        ],
        "format": RecommendationPlan.model_json_schema(),
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
        )

    response.raise_for_status()

    data = response.json()
    content = data["message"]["content"]

    plan = RecommendationPlan.model_validate_json(
        content
    )

    return plan.fact_ids
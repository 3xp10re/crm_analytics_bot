import asyncio

from app.llm_recommendations import select_recommendations_with_llm
from app.recommendation_facts import collect_recommendation_facts


async def get_recommendations() -> list[str]:
    facts = await asyncio.to_thread(
        collect_recommendation_facts
    )

    if not facts:
        return []

    facts_by_id = {
        fact.id: fact
        for fact in facts
    }

    try:
        selected_ids = await select_recommendations_with_llm(
            facts
        )
    except Exception as error:
        print(
            "Ошибка LLM-рекомендаций:",
            repr(error),
        )

        selected_ids = []

    recommendations = []
    used_ids = set()

    for fact_id in selected_ids:
        if fact_id not in facts_by_id:
            continue

        if fact_id in used_ids:
            continue

        recommendations.append(
            facts_by_id[fact_id].text
        )

        used_ids.add(fact_id)

        if len(recommendations) == 5:
            break

    if recommendations:
        return recommendations

    sorted_facts = sorted(
        facts,
        key=lambda fact: fact.priority,
        reverse=True,
    )

    return [
        fact.text
        for fact in sorted_facts[:5]
    ]
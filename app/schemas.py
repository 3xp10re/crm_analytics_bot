from typing import Literal, Any

from pydantic import BaseModel, Field


class QueryIntent(BaseModel):
    intent: Literal[
        "revenue",
        "cancelled_orders",
        "best_manager_by_margin",
        "top_source_by_orders",
        "city_highest_average_check",
        "unsupported",
    ]

    start_date: str | None
    end_date: str | None
    unsupported_reason: str


class RecommendationFact(BaseModel):
    id: str
    category: str
    priority: float
    text: str
    evidence: dict[str, Any]


class RecommendationPlan(BaseModel):
    fact_ids: list[str] = Field(
        min_length=1,
        max_length=5,
    )
from typing import Literal

from pydantic import BaseModel


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
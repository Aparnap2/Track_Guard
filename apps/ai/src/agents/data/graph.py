"""Data Analytics agent — answers questions about user engagement, cohorts, churn, and KPIs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DataGraph:
    """Data analytics specialist agent — handles @data mentions.

    Answers questions about user engagement, cohort analysis, churn,
    conversion metrics, KPIs, and product analytics.
    """

    system_prompt: str = (
        "You are a startup data analytics specialist. Answer questions about "
        "user engagement, cohort analysis, churn, conversion funnels, "
        "retention metrics, KPIs, and product analytics. "
        "Be specific with metrics and caveat any assumptions about data sources."
    )

    async def invoke(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Answer a data analytics question via LLM."""
        from src.config.llm import chat_completion

        question = input_data.get("question", "")
        tenant_id = input_data.get("tenant_id", "default")

        response = await chat_completion(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": question},
            ],
            tenant_id=tenant_id,
        )

        return {"answer": response, "output_message": response, "agent_type": "data"}

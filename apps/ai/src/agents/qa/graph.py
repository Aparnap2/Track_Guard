"""QA agent graph — answers questions via LLM."""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field

from src.agents.qa.state import QAState
from src.config.llm import chat_completion

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the IterateSwarm Q&A Agent. You answer questions about the business.

You have access to financial data, metrics, and business context.

Rules:
1. Be concise and direct. Answer in 2-3 sentences max.
2. If you don't have specific data, say so clearly — do not hallucinate numbers.
3. Format numbers with commas and currency symbols where appropriate.
4. Always cite your data source or state if you're making a general observation.
"""


@dataclass
class QAGraph:
    tenant_id: str

    def invoke(self, state: QAState) -> QAState:
        """Run the QA agent synchronously."""
        tenant_id = state.get("tenant_id", self.tenant_id)
        question = state.get("question", "")

        log.info("QAGraph invoking for tenant %s: %s", tenant_id, question[:80])

        if not question:
            state["answer"] = "No question provided."
            state["error"] = "question is empty"
            return state

        user_prompt = f"""Question: {question}

Tenant: {tenant_id}

Answer the question based on your knowledge of the business. If you don't have specific data, explain what data would be needed."""

        try:
            start = time.time()
            answer = chat_completion(
                model=None,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            elapsed = time.time() - start

            log.info("QAGraph completed in %.2fs: %s", elapsed, answer[:100])

            state["answer"] = answer
            state["matched_category"] = "general_qa"
            state["slack_message"] = f"*Q&A Answer*\n> {question}\n\n{answer}"
            state["slack_blocks"] = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Q&A Answer*\n> {question}\n\n{answer}"},
                }
            ]

        except Exception as e:
            log.error("QAGraph LLM call failed: %s", e)
            state["error"] = str(e)
            state["answer"] = f"I encountered an error processing your question: {e}"

        return state


qa_graph = QAGraph(tenant_id="")

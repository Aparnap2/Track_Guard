"""QA state for LangGraph."""
from typing import TypedDict


class QAState(TypedDict, total=False):
    tenant_id: str
    question: str
    matched_category: str
    data_context: str
    memory_context: str
    answer: str
    slack_message: str
    slack_blocks: list
    error: str
    retry_count: int
    langfuse_trace_id: str
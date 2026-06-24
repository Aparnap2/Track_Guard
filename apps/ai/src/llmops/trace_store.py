from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from src.llmops.failure_buckets import FailureBucket


@dataclass
class AgentTrace:
    trace_id: str
    tenant_id: str
    agent_name: str
    action: str
    duration_ms: float
    llm_calls: int
    llm_tokens: int
    llm_cost_usd: float
    status: Literal["success", "failed", "partial"]
    failure_bucket: FailureBucket | None = None
    error: str | None = None
    created_at: str = ""


_trace_store: list[AgentTrace] = []


def record_trace(trace: AgentTrace) -> None:
    if not trace.created_at:
        trace.created_at = datetime.now(timezone.utc).isoformat()
    _trace_store.append(trace)


def get_traces(
    tenant_id: str | None = None,
    agent_name: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[AgentTrace]:
    results = list(_trace_store)
    if tenant_id is not None:
        results = [t for t in results if t.tenant_id == tenant_id]
    if agent_name is not None:
        results = [t for t in results if t.agent_name == agent_name]
    if status is not None:
        results = [t for t in results if t.status == status]
    results.sort(key=lambda t: t.created_at, reverse=True)
    return results[:limit]


def get_trace_summary(tenant_id: str | None = None) -> dict:
    traces = list(_trace_store)
    if tenant_id is not None:
        traces = [t for t in traces if t.tenant_id == tenant_id]

    total = len(traces)
    if total == 0:
        return {
            "total_traces": 0,
            "success_rate": 0.0,
            "avg_duration_ms": 0.0,
            "total_cost_usd": 0.0,
            "failure_buckets": {},
        }

    successes = sum(1 for t in traces if t.status == "success")
    total_duration = sum(t.duration_ms for t in traces)
    total_cost = sum(t.llm_cost_usd for t in traces)

    failure_buckets: dict[str, int] = {}
    for t in traces:
        if t.failure_bucket is not None:
            key = t.failure_bucket.value
            failure_buckets[key] = failure_buckets.get(key, 0) + 1

    return {
        "total_traces": total,
        "success_rate": round(successes / total, 4) if total > 0 else 0.0,
        "avg_duration_ms": round(total_duration / total, 1) if total > 0 else 0.0,
        "total_cost_usd": round(total_cost, 6),
        "failure_buckets": failure_buckets,
    }

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from src.llmops.failure_buckets import FailureBucket, _classify_error, record_failure
from src.llmops.trace_store import AgentTrace, record_trace


def capture_execution_error(
    action_type: str,
    error: Exception,
    tenant_id: str,
    context: dict | None = None,
) -> dict:
    bucket = _classify_error(error)
    trace_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()

    record_failure(
        tenant_id=tenant_id,
        bucket=bucket,
        source=action_type,
        operation=action_type,
        error_message=str(error),
        trace_id=trace_id,
    )

    trace = AgentTrace(
        trace_id=trace_id,
        tenant_id=tenant_id,
        agent_name=action_type,
        action=action_type,
        duration_ms=0.0,
        llm_calls=0,
        llm_tokens=0,
        llm_cost_usd=0.0,
        status="failed",
        failure_bucket=bucket,
        error=str(error),
        created_at=now,
    )
    record_trace(trace)

    return {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "bucket": bucket.value,
        "trace_id": trace_id,
        "timestamp": now,
    }


def format_errors_for_context(errors: list[dict], max_errors: int = 3) -> list[dict]:
    sorted_errors = sorted(
        errors, key=lambda e: e.get("timestamp", ""), reverse=True
    )[:max_errors]

    result: list[dict] = []
    for err in sorted_errors:
        msg = err.get("error_message", "")
        if len(msg) > 500:
            msg = msg[:497] + "..."
        result.append({
            "error_type": err.get("error_type", "Unknown"),
            "error_message": msg,
            "bucket": err.get("bucket", "unknown"),
            "trace_id": err.get("trace_id", ""),
            "timestamp": err.get("timestamp", ""),
        })

    return result

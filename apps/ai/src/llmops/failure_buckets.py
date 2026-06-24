from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class FailureBucket(str, Enum):
    DATA_QUALITY = "data_quality"
    REASONING_FAILURE = "reasoning_failure"
    RULES_INTERPRETATION = "rules_interpretation"
    CONTEXT_ASSEMBLY_ERROR = "context_assembly_error"
    WRONG_TOOL_SELECTION = "wrong_tool_selection"
    APPROVAL_POLICY_ERROR = "approval_policy_error"
    NARRATIVE_QUALITY = "narrative_quality"
    CORRELATION_MISS = "correlation_miss"
    UNKNOWN = "unknown"


@dataclass
class FailureEvent:
    id: str
    tenant_id: str
    bucket: FailureBucket
    source: str
    operation: str
    error_message: str
    trace_id: str
    created_at: str
    resolved: bool = False
    resolution: str | None = None


_failure_store: dict[str, FailureEvent] = {}


def record_failure(
    tenant_id: str,
    bucket: FailureBucket,
    source: str,
    operation: str,
    error_message: str,
    trace_id: str = "",
) -> FailureEvent:
    event = FailureEvent(
        id=uuid.uuid4().hex[:12],
        tenant_id=tenant_id,
        bucket=bucket,
        source=source,
        operation=operation,
        error_message=error_message,
        trace_id=trace_id or uuid.uuid4().hex[:12],
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _failure_store[event.id] = event
    return event


def get_failures(
    tenant_id: str | None = None,
    bucket: FailureBucket | None = None,
    limit: int = 100,
) -> list[FailureEvent]:
    results = list(_failure_store.values())
    if tenant_id is not None:
        results = [e for e in results if e.tenant_id == tenant_id]
    if bucket is not None:
        results = [e for e in results if e.bucket == bucket]
    results.sort(key=lambda e: e.created_at, reverse=True)
    return results[:limit]


def get_failure_summary(tenant_id: str | None = None) -> dict[str, int]:
    summary: dict[str, int] = {}
    events = list(_failure_store.values())
    if tenant_id is not None:
        events = [e for e in events if e.tenant_id == tenant_id]
    for event in events:
        bucket_key = event.bucket.value
        summary[bucket_key] = summary.get(bucket_key, 0) + 1
    return summary


def resolve_failure(failure_id: str, resolution: str) -> bool:
    event = _failure_store.get(failure_id)
    if event is None:
        return False
    event.resolved = True
    event.resolution = resolution
    return True


def clear_failures() -> int:
    count = len(_failure_store)
    _failure_store.clear()
    return count


def _classify_error(error: Exception) -> FailureBucket:
    error_type = type(error).__name__.lower()
    error_str = str(error).lower()
    combined = f"{error_type} {error_str}"

    data_quality_keywords = [
        "connection", "timeout", "refused", "econnrefused",
        "econnreset", "socket", "dns", "resolve", "parse",
        "decode", "encoding", "deserialize", "serialize",
        "broken pipe", "network", "eof", "eoferror",
    ]
    context_assembly_keywords = [
        "keyerror", "key error", "attributeerror", "attribute error",
        "indexerror", "index out of", "nameerror", "name error",
        "lookup", "not found", "missing",
    ]
    rules_interpretation_keywords = [
        "threshold", "policy", "validation", "constraint",
        "violation", "not allowed", "invalid value",
    ]
    wrong_tool_keywords = [
        "routing", "dispatch", "no tool", "unsupported",
        "not implemented", "abstract", "unknown action",
    ]
    approval_policy_keywords = [
        "authorization", "permission", "forbidden", "access denied",
        "unauthorized", "not authorized", "forbidden",
    ]
    narrative_quality_keywords = [
        "template", "render", "format", "hallucination",
        "jinja", "moustache", "string format",
    ]
    reasoning_keywords = [
        "assertion", "logic", "calculation", "assertionerror",
        "zerodivisionerror", "division by zero",
        "overflow", "underflow", "arithmetic",
    ]

    if any(k in combined for k in data_quality_keywords):
        return FailureBucket.DATA_QUALITY
    if any(k in combined for k in context_assembly_keywords):
        return FailureBucket.CONTEXT_ASSEMBLY_ERROR
    if any(k in combined for k in rules_interpretation_keywords):
        return FailureBucket.RULES_INTERPRETATION
    if any(k in combined for k in wrong_tool_keywords):
        return FailureBucket.WRONG_TOOL_SELECTION
    if any(k in combined for k in approval_policy_keywords):
        return FailureBucket.APPROVAL_POLICY_ERROR
    if any(k in combined for k in narrative_quality_keywords):
        return FailureBucket.NARRATIVE_QUALITY
    if any(k in combined for k in reasoning_keywords):
        return FailureBucket.REASONING_FAILURE

    return FailureBucket.UNKNOWN

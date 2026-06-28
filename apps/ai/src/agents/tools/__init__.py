"""Tool registry for Sarthi agent actions.

Each tool is a standalone async function with a tool_def dict for metadata.
Tools are registered in TOOL_REGISTRY and wired to HITL manager for resolution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class ToolDef:
    """Definition of a callable tool with HITL tier routing metadata.

    Attributes:
        name: Unique tool name (snake_case).
        description: Human-readable description of what the tool does.
        hitl_tier: HITL tier — one of "auto", "review", "approve", "blocked".
            Must match the string returned by HITLManager.route().
        fn: Async function that executes the tool. Takes tenant_id as first arg.
        trigger_patterns: Alert pattern IDs that suggest this tool
            (e.g. "FG-05", "BG-04").
    """
    name: str
    description: str
    hitl_tier: str
    fn: Callable[..., Coroutine[Any, Any, dict[str, Any]]]
    trigger_patterns: list[str] = field(default_factory=list)


TOOL_REGISTRY: dict[str, ToolDef] = {}


def register_tool(tool: ToolDef) -> None:
    """Register a tool in the global TOOL_REGISTRY."""
    TOOL_REGISTRY[tool.name] = tool


def get_tools_for_tier(tier: str) -> list[ToolDef]:
    """Get all tools whose HITL tier matches the given routing decision."""
    return [t for t in TOOL_REGISTRY.values() if t.hitl_tier == tier]


def get_tools_for_pattern(pattern_id: str) -> list[ToolDef]:
    """Get all tools whose trigger_patterns include the given pattern ID."""
    return [t for t in TOOL_REGISTRY.values() if pattern_id in t.trigger_patterns]


def get_tools_for_patterns(pattern_ids: list[str]) -> list[ToolDef]:
    """Get all tools matching any of the given triggered pattern IDs."""
    matched: dict[str, ToolDef] = {}
    for pid in pattern_ids:
        for t in TOOL_REGISTRY.values():
            if pid in t.trigger_patterns and t.name not in matched:
                matched[t.name] = t
    return list(matched.values())


# Auto-register all tool modules on import
from . import pause_payment_retry
from . import draft_investor_update
from . import schedule_customer_checkin
from . import flag_churn_risk

for _mod in [pause_payment_retry, draft_investor_update,
             schedule_customer_checkin, flag_churn_risk]:
    register_tool(ToolDef(**_mod.tool_def, fn=_mod.execute))

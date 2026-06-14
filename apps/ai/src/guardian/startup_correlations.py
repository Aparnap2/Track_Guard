"""5 cross-functional correlations for Startup Guardian.

Each correlation is a pure function: ``(state: dict) -> list[correlation_dict]``
that detects patterns across two or more domains.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def cr_support_execution(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    support = state.get("support", {})
    execution = state.get("execution", {})
    if support.get("unresolved_issues", 0) > 5 and execution.get("overdue_tasks", 0) > 3:
        return [{"id": "SG-CR-01", "title": "Team overwhelmed", "severity": "high",
                 "domains": ["support", "execution"],
                 "detail": "High unresolved issues + overdue tasks suggests team is overloaded",
                 "recommendation": "Review team capacity and prioritize sprint backlog"}]
    return []


def cr_revenue_support(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    revenue = state.get("revenue", {})
    support = state.get("support", {})
    if revenue.get("trend") == "declining" and support.get("unresolved_issues", 0) > 5:
        return [{"id": "SG-CR-02", "title": "Product quality impacting revenue", "severity": "critical",
                 "domains": ["revenue", "support"],
                 "detail": "Revenue declining alongside high support load suggests product issues",
                 "recommendation": "Audit top support issues for product improvement opportunities"}]
    return []


def cr_finance_execution(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    finance = state.get("finance", {})
    execution = state.get("execution", {})
    if finance.get("total_overdue_cents", 0) > 5_000_000 and execution.get("health") == "blocked":
        return [{"id": "SG-CR-03", "title": "Cash flow impacting delivery", "severity": "critical",
                 "domains": ["finance", "execution"],
                 "detail": "High overdue receivables and blocked execution suggest cash constraints",
                 "recommendation": "Expedite collections and review project budgets"}]
    return []


def cr_team_finance(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    team = state.get("team", {})
    finance = state.get("finance", {})
    if team.get("departures_30d", 0) > 1 and finance.get("total_overdue_cents", 0) > 5_000_000:
        return [{"id": "SG-CR-04", "title": "Cash crunch driving attrition", "severity": "high",
                 "domains": ["team", "finance"],
                 "detail": "Departures coinciding with high receivables suggests cash concerns",
                 "recommendation": "Review compensation and communicate financial runway transparently"}]
    return []


def cr_revenue_execution(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    revenue = state.get("revenue", {})
    execution = state.get("execution", {})
    if revenue.get("trend") == "declining" and execution.get("health") in ("at_risk", "blocked"):
        return [{"id": "SG-CR-05", "title": "Strategic risk: market fit vs execution", "severity": "high",
                 "domains": ["revenue", "execution"],
                 "detail": "Revenue declining alongside execution challenges",
                 "recommendation": "Strategic review: is this a product-market fit or execution issue?"}]
    return []


STARTUP_CORRELATION_FUNCTIONS = [
    cr_support_execution, cr_revenue_support, cr_finance_execution,
    cr_team_finance, cr_revenue_execution,
]


def run_correlations(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    correlations: List[Dict[str, Any]] = []
    for cr_fn in STARTUP_CORRELATION_FUNCTIONS:
        try:
            correlations.extend(cr_fn(state))
        except Exception:
            logger.exception("Correlation %s failed", cr_fn.__name__)
    return correlations

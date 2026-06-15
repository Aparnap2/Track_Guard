"""8 deterministic watchlists for Startup Guardian.

Each watchlist is a pure function: ``(state: dict) -> list[alert_dict]``
that inspects a MissionStateV2 dict and returns zero or more alert dicts.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def wl_support_overload(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    support = state.get("support", {})
    unresolved = support.get("unresolved_issues", 0)
    if unresolved > 10:
        return [{"id": "SG-SUP-01", "title": "Support overload", "severity": "high",
                 "detail": f"{unresolved} unresolved issues", "domain": "support"}]
    return []


def wl_support_sla_breaches(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    sla = state.get("support", {}).get("sla_breach_count", 0)
    if sla > 0:
        return [{"id": "SG-SUP-02", "title": "SLA breaches detected", "severity": "critical",
                 "detail": f"{sla} SLA breaches", "domain": "support"}]
    return []


def wl_execution_overdue(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    overdue = state.get("execution", {}).get("overdue_tasks", 0)
    if overdue > 5:
        return [{"id": "SG-EXE-01", "title": "Execution slippage", "severity": "high",
                 "detail": f"{overdue} overdue tasks", "domain": "execution"}]
    return []


def wl_execution_blocked(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    health = state.get("execution", {}).get("health", "on_track")
    if health == "blocked":
        return [{"id": "SG-EXE-02", "title": "Execution blocked", "severity": "critical",
                 "detail": "Project execution is blocked", "domain": "execution"}]
    return []


def wl_finance_overdue(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    overdue_cents = state.get("finance", {}).get("total_overdue_cents", 0)
    if overdue_cents > 5_000_000:
        return [{"id": "SG-FIN-01", "title": "High overdue receivables", "severity": "high",
                 "detail": f"₹{overdue_cents // 100:,} overdue", "domain": "finance"}]
    return []


def wl_finance_cash_crunch(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    dso = state.get("finance", {}).get("days_sales_outstanding")
    if dso is not None and dso > 60:
        return [{"id": "SG-FIN-02", "title": "DSO warning", "severity": "medium",
                 "detail": f"DSO at {dso:.0f} days", "domain": "finance"}]
    return []


def wl_revenue_declining(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    trend = state.get("revenue", {}).get("trend", "stable")
    if trend == "declining":
        return [{"id": "SG-REV-01", "title": "Revenue declining", "severity": "critical",
                 "detail": "Revenue trend is declining", "domain": "revenue"}]
    return []


def wl_team_attrition(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    departures = state.get("team", {}).get("departures_30d", 0)
    if departures > 2:
        return [{"id": "SG-TEAM-01", "title": "Team attrition spike", "severity": "high",
                 "detail": f"{departures} departures in 30 days", "domain": "team"}]
    return []


STARTUP_WATCHLIST_FUNCTIONS = [
    wl_support_overload, wl_support_sla_breaches,
    wl_execution_overdue, wl_execution_blocked,
    wl_finance_overdue, wl_finance_cash_crunch,
    wl_revenue_declining, wl_team_attrition,
]


def run_watchlists(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    for wl_fn in STARTUP_WATCHLIST_FUNCTIONS:
        try:
            alerts.extend(wl_fn(state))
        except Exception:
            logger.exception("Watchlist %s failed", wl_fn.__name__)
    return alerts

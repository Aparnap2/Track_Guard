"""
Pydantic V2 schemas for MissionState V2 — Startup Guardian domain states.

These models represent the 5 domain states aggregated by the Startup Guardian
orchestrator from ERPNext, QuickBooks, HubSpot, and other data sources.

All domain states degrade gracefully — zero values on construction, not None.
All metric fields have sensible defaults (0, empty dict, GOOD/ON_TRACK/HEALTHY).

Usage:
    from src.states.schemas import MissionStateV2, SupportState, SupportHealth

    state = MissionStateV2(
        tenant_id="startup_abc",
        support=SupportState(open_issues=3, health=SupportHealth.ATTENTION),
        execution=ExecutionState(overdue_tasks=2, health=ExecutionHealth.AT_RISK),
    )

    print(state.overall_health)  # SupportHealth.GOOD (default)
    print(state.support.health)  # SupportHealth.ATTENTION
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Domain Enums
# =============================================================================

class SupportHealth(str, Enum):
    """Health status for support operations."""
    GOOD = "good"
    ATTENTION = "attention"
    CRITICAL = "critical"


class ExecutionHealth(str, Enum):
    """Health status for project/task execution."""
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BLOCKED = "blocked"


class FinancialHealth(str, Enum):
    """Health status for financial operations."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class RevenueTrend(str, Enum):
    """Trend direction for revenue."""
    GROWING = "growing"
    STABLE = "stable"
    DECLINING = "declining"


# =============================================================================
# Domain State Models
# =============================================================================

class SupportState(BaseModel):
    """Aggregated state from ERPNext Helpdesk (Issues).

    Tracks open tickets, SLA breaches, and resolution velocity.
    Used by the Guardian orchestrator to determine support health.

    Attributes:
        open_issues: Total open issues currently in the helpdesk.
        unresolved_issues: Issues past SLA or still open beyond target.
        sla_breach_count: Number of SLA breaches in the current window.
        avg_resolution_hours: Average time to resolve (nullable if no data).
        health: Computed health status for the support domain.
    """
    open_issues: int = 0
    unresolved_issues: int = 0
    sla_breach_count: int = 0
    avg_resolution_hours: Optional[float] = None
    health: SupportHealth = SupportHealth.GOOD


class ExecutionState(BaseModel):
    """Aggregated state from ERPNext Projects/Tasks.

    Tracks project milestones, overdue tasks, and completion velocity.
    Used by the Guardian orchestrator to determine execution health.

    Attributes:
        active_projects: Number of currently active projects.
        overdue_tasks: Tasks past their due date.
        open_tasks: Total open (not yet completed) tasks.
        completed_tasks_30d: Tasks completed in the last 30 days.
        avg_completion_pct: Average completion percentage across projects.
        health: Computed health status for the execution domain.
    """
    active_projects: int = 0
    overdue_tasks: int = 0
    open_tasks: int = 0
    completed_tasks_30d: int = 0
    avg_completion_pct: Optional[float] = None
    health: ExecutionHealth = ExecutionHealth.ON_TRACK


class TeamState(BaseModel):
    """Aggregated state from ERPNext HR (Employees).

    Tracks headcount, hiring velocity, and attrition.
    Used by the Guardian orchestrator to determine team health.

    Attributes:
        active_employees: Number of currently active employees.
        headcount_by_department: Map of department name to headcount.
        new_hires_30d: Employees hired in the last 30 days.
        departures_30d: Employees who left in the last 30 days.
        health: Computed health status for the team domain.
    """
    active_employees: int = 0
    headcount_by_department: dict[str, int] = {}
    new_hires_30d: int = 0
    departures_30d: int = 0
    health: SupportHealth = SupportHealth.GOOD


class FinanceState(BaseModel):
    """Aggregated state from Sales Invoices + QuickBooks.

    Tracks outstanding receivables, overdue payments, and DSO.
    All monetary values are in **cents** (smallest currency unit) to
    avoid floating-point rounding errors.

    Attributes:
        outstanding_invoices: Total invoices not yet paid.
        total_outstanding_cents: Sum of all outstanding invoice amounts (cents).
        overdue_invoices: Invoices past their due date.
        total_overdue_cents: Sum of all overdue invoice amounts (cents).
        unpaid_invoices_30d_cents: Unpaid invoices raised in last 30 days (cents).
        paid_invoices_30d_cents: Paid invoices collected in last 30 days (cents).
        days_sales_outstanding: DSO in days (nullable if insufficient data).
        health: Computed health status for the finance domain.
    """
    outstanding_invoices: int = 0
    total_outstanding_cents: int = 0
    overdue_invoices: int = 0
    total_overdue_cents: int = 0
    unpaid_invoices_30d_cents: int = 0
    paid_invoices_30d_cents: int = 0
    days_sales_outstanding: Optional[float] = None
    health: FinancialHealth = FinancialHealth.HEALTHY


class RevenueState(BaseModel):
    """Aggregated state from HubSpot CRM.

    Tracks deal pipeline, closed-won revenue, MRR, and active customers.
    All monetary values are in **cents** (smallest currency unit).

    Attributes:
        total_deals_cents: Total value of all deals in the pipeline (cents).
        won_deals_30d_cents: Value of deals closed-won in last 30 days (cents).
        pipeline_deals_cents: Value of open pipeline deals (cents).
        active_customers: Number of currently active/paying customers.
        mrr_cents: Monthly recurring revenue in cents (nullable if unknown).
        trend: Revenue trend direction.
    """
    total_deals_cents: int = 0
    won_deals_30d_cents: int = 0
    pipeline_deals_cents: int = 0
    active_customers: int = 0
    mrr_cents: Optional[int] = None
    trend: RevenueTrend = RevenueTrend.STABLE


# =============================================================================
# Unified MissionState V2
# =============================================================================

class MissionStateV2(BaseModel):
    """Unified startup state — the single source of truth for Startup Guardian.

    Assembled by the orchestrator from 5 domain states, then consumed by
    watchlists, correlations, and Slack delivery.

    All domain states default to empty/healthy construction so that a
    MissionStateV2(tenant_id="...") is always valid.

    Attributes:
        tenant_id: The tenant/organization this state belongs to.
        run_id: Unique run identifier for this state assembly cycle.
        timestamp: When this state was assembled (UTC).
        support: Aggregated SupportState from ERPNext Helpdesk.
        execution: Aggregated ExecutionState from ERPNext Projects/Tasks.
        team: Aggregated TeamState from ERPNext HR.
        finance: Aggregated FinanceState from Sales Invoices + QuickBooks.
        revenue: Aggregated RevenueState from HubSpot CRM.
        overall_health: Cross-domain health computed by the orchestrator.
        alert_count: Number of active alerts across all domains.
        correlation_count: Number of cross-domain correlations detected.
        connectors_ok: Health status of each data connector (name -> ok).
        raw_snapshots: Raw API responses for debugging/audit (optional).
    """
    tenant_id: str
    run_id: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Domain states
    support: SupportState = Field(default_factory=SupportState)
    execution: ExecutionState = Field(default_factory=ExecutionState)
    team: TeamState = Field(default_factory=TeamState)
    finance: FinanceState = Field(default_factory=FinanceState)
    revenue: RevenueState = Field(default_factory=RevenueState)

    # Cross-domain health (computed by orchestrator)
    overall_health: SupportHealth = SupportHealth.GOOD
    alert_count: int = 0
    correlation_count: int = 0

    # Connector health
    connectors_ok: dict[str, bool] = {}

    # Raw snapshots (optional — for debugging/audit)
    raw_snapshots: dict[str, Any] = {}

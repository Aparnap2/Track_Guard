"""Unit tests for the Startup Guardian orchestrator core logic."""
import os
from unittest.mock import patch

import pytest


def _build_test_state(support_count=0, exec_overdue=0, team_count=0,
                       finance_overdue=0, revenue_won=0, rev_pipeline=0):
    """Build a raw snapshot dict for a fake ERPNext response."""
    return {
        "support_open_issues": support_count,
        "support_unresolved_issues": support_count,
        "execution_active_projects": 3,
        "execution_overdue_tasks": exec_overdue,
        "execution_avg_completion": 50.0,
        "team_active_count": team_count,
        "team_departments": {"Eng": 5},
        "team_new_joinees_30d": 1,
        "finance_unpaid_cents": 100000,
        "finance_overdue_cents": finance_overdue,
        "finance_total_outstanding_cents": 150000,
    }


class TestOrchestratorCore:
    """Tests the orchestrator's state assembly logic directly, bypassing asyncio.to_thread."""

    def test_assemble_support_is_critical(self):
        from src.guardian.assemblers import assemble_support_state
        result = assemble_support_state({"support_open_issues": 20, "support_unresolved_issues": 10})
        assert result.health.value == "critical"

    def test_assemble_execution_is_blocked(self):
        from src.guardian.assemblers import assemble_execution_state
        result = assemble_execution_state({"execution_overdue_tasks": 5})
        assert result.health.value == "blocked"

    def test_assemble_finance_is_critical(self):
        from src.guardian.assemblers import assemble_finance_state
        result = assemble_finance_state({"finance_overdue_cents": 2_000_000})
        assert result.health.value == "critical"

    def test_assemble_revenue_is_growing(self):
        from src.guardian.assemblers import assemble_revenue_state
        result = assemble_revenue_state({
            "revenue_total_deals_cents": 100000000,
            "revenue_won_deals_30d_cents": 50000000,
            "revenue_pipeline_deals_cents": 100000000,
            "revenue_active_customers": 5,
        })
        assert result.trend.value == "growing"

    def test_full_pipeline_assembly(self):
        from src.states.schemas import MissionStateV2
        from src.guardian.assemblers import (
            assemble_support_state, assemble_execution_state,
            assemble_team_state, assemble_finance_state, assemble_revenue_state,
        )

        state = MissionStateV2(tenant_id="test-tenant")
        state.support = assemble_support_state({"support_open_issues": 5, "support_unresolved_issues": 2})
        state.execution = assemble_execution_state({"execution_active_projects": 3, "execution_overdue_tasks": 1, "execution_avg_completion": 50.0})
        state.team = assemble_team_state({"team_active_count": 10, "team_departments": {"Eng": 5}, "team_new_joinees_30d": 1})
        state.finance = assemble_finance_state({"finance_unpaid_cents": 100000, "finance_overdue_cents": 50000, "finance_total_outstanding_cents": 150000})
        state.revenue = assemble_revenue_state({"revenue_total_deals_cents": 100000000, "revenue_won_deals_30d_cents": 30000000, "revenue_pipeline_deals_cents": 70000000, "revenue_active_customers": 5})

        result = state.model_dump()
        assert result["tenant_id"] == "test-tenant"
        assert result["support"]["open_issues"] == 5
        assert result["execution"]["active_projects"] == 3
        assert result["team"]["active_employees"] == 10
        assert result["finance"]["total_outstanding_cents"] == 150000
        assert result["revenue"]["total_deals_cents"] == 100000000

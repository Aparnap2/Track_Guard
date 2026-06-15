"""Unit tests for Startup Guardian assembler functions."""
from src.states.schemas import (
    SupportState, SupportHealth,
    ExecutionState, ExecutionHealth,
    TeamState,
    FinanceState, FinancialHealth,
    RevenueState, RevenueTrend,
)


class TestAssembleSupportState:
    def test_support_good(self):
        from src.guardian.assemblers import assemble_support_state
        result = assemble_support_state({"support_open_issues": 2, "support_unresolved_issues": 0})
        assert isinstance(result, SupportState)
        assert result.health == SupportHealth.GOOD

    def test_support_attention(self):
        from src.guardian.assemblers import assemble_support_state
        result = assemble_support_state({"support_open_issues": 10, "support_unresolved_issues": 3})
        assert result.health == SupportHealth.ATTENTION

    def test_support_critical(self):
        from src.guardian.assemblers import assemble_support_state
        result = assemble_support_state({"support_open_issues": 20, "support_unresolved_issues": 10})
        assert result.health == SupportHealth.CRITICAL

    def test_support_empty_dict(self):
        from src.guardian.assemblers import assemble_support_state
        result = assemble_support_state({})
        assert result.open_issues == 0
        assert result.health == SupportHealth.GOOD


class TestAssembleExecutionState:
    def test_execution_on_track(self):
        from src.guardian.assemblers import assemble_execution_state
        result = assemble_execution_state({"execution_overdue_tasks": 0, "execution_active_projects": 5})
        assert result.health == ExecutionHealth.ON_TRACK

    def test_execution_at_risk(self):
        from src.guardian.assemblers import assemble_execution_state
        result = assemble_execution_state({"execution_overdue_tasks": 2, "execution_active_projects": 5})
        assert result.health == ExecutionHealth.AT_RISK

    def test_execution_blocked(self):
        from src.guardian.assemblers import assemble_execution_state
        result = assemble_execution_state({"execution_overdue_tasks": 5, "execution_active_projects": 5})
        assert result.health == ExecutionHealth.BLOCKED


class TestAssembleTeamState:
    def test_team_department_mapping(self):
        from src.guardian.assemblers import assemble_team_state
        result = assemble_team_state({"team_active_count": 10, "team_departments": {"Engineering": 5}, "team_new_joinees_30d": 1})
        assert result.active_employees == 10
        assert result.headcount_by_department["Engineering"] == 5
        assert result.new_hires_30d == 1

    def test_team_empty_dict(self):
        from src.guardian.assemblers import assemble_team_state
        result = assemble_team_state({})
        assert result.active_employees == 0
        assert result.headcount_by_department == {}


class TestAssembleFinanceState:
    def test_finance_healthy(self):
        from src.guardian.assemblers import assemble_finance_state
        result = assemble_finance_state({"finance_total_outstanding_cents": 100000, "finance_overdue_cents": 0})
        assert result.health == FinancialHealth.HEALTHY

    def test_finance_warning(self):
        from src.guardian.assemblers import assemble_finance_state
        result = assemble_finance_state({"finance_overdue_cents": 500000})
        assert result.health == FinancialHealth.WARNING

    def test_finance_critical(self):
        from src.guardian.assemblers import assemble_finance_state
        result = assemble_finance_state({"finance_overdue_cents": 2000000})
        assert result.health == FinancialHealth.CRITICAL


class TestAssembleRevenueState:
    def test_revenue_growing(self):
        from src.guardian.assemblers import assemble_revenue_state
        result = assemble_revenue_state({"revenue_won_deals_30d_cents": 50000000, "revenue_pipeline_deals_cents": 100000000})
        assert result.trend == RevenueTrend.GROWING

    def test_revenue_stable(self):
        from src.guardian.assemblers import assemble_revenue_state
        result = assemble_revenue_state({"revenue_won_deals_30d_cents": 10000000, "revenue_pipeline_deals_cents": 100000000})
        assert result.trend == RevenueTrend.STABLE

    def test_revenue_declining(self):
        from src.guardian.assemblers import assemble_revenue_state
        result = assemble_revenue_state({"revenue_won_deals_30d_cents": 0, "revenue_pipeline_deals_cents": 50000000})
        assert result.trend == RevenueTrend.DECLINING

    def test_revenue_empty(self):
        from src.guardian.assemblers import assemble_revenue_state
        result = assemble_revenue_state({})
        assert result.mrr_cents is None
        assert result.trend == RevenueTrend.STABLE

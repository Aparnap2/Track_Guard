"""Unit tests for Startup Guardian correlation functions."""
from src.guardian.startup_correlations import run_correlations


class TestRunCorrelations:
    def test_healthy_state_no_correlations(self):
        healthy = {
            "support": {"unresolved_issues": 1},
            "execution": {"overdue_tasks": 0, "health": "on_track"},
            "finance": {"total_overdue_cents": 1000},
            "revenue": {"trend": "stable"},
            "team": {"departures_30d": 0},
        }
        result = run_correlations(healthy)
        assert result == []

    def test_support_execution_correlation(self):
        state = {
            "support": {"unresolved_issues": 10},
            "execution": {"overdue_tasks": 5, "health": "at_risk"},
            "finance": {"total_overdue_cents": 0},
            "revenue": {"trend": "stable"},
            "team": {"departures_30d": 0},
        }
        result = run_correlations(state)
        assert any(c["id"] == "SG-CR-01" for c in result)

    def test_revenue_support_correlation(self):
        state = {
            "support": {"unresolved_issues": 10},
            "execution": {"overdue_tasks": 0, "health": "on_track"},
            "finance": {"total_overdue_cents": 0},
            "revenue": {"trend": "declining"},
            "team": {"departures_30d": 0},
        }
        result = run_correlations(state)
        assert any(c["id"] == "SG-CR-02" for c in result)

    def test_finance_execution_correlation(self):
        state = {
            "support": {"unresolved_issues": 0},
            "execution": {"overdue_tasks": 0, "health": "blocked"},
            "finance": {"total_overdue_cents": 10_000_000},
            "revenue": {"trend": "stable"},
            "team": {"departures_30d": 0},
        }
        result = run_correlations(state)
        assert any(c["id"] == "SG-CR-03" for c in result)

    def test_team_finance_correlation(self):
        state = {
            "support": {"unresolved_issues": 0},
            "execution": {"overdue_tasks": 0, "health": "on_track"},
            "finance": {"total_overdue_cents": 10_000_000},
            "revenue": {"trend": "stable"},
            "team": {"departures_30d": 2},
        }
        result = run_correlations(state)
        assert any(c["id"] == "SG-CR-04" for c in result)

    def test_revenue_execution_correlation(self):
        state = {
            "support": {"unresolved_issues": 0},
            "execution": {"overdue_tasks": 0, "health": "blocked"},
            "finance": {"total_overdue_cents": 0},
            "revenue": {"trend": "declining"},
            "team": {"departures_30d": 0},
        }
        result = run_correlations(state)
        assert any(c["id"] == "SG-CR-05" for c in result)

"""Unit tests for combined Startup Guardian detector."""
from src.guardian.startup_detector import run_startup_detector


class TestRunStartupDetector:
    def test_healthy_state(self):
        healthy = {
            "support": {"unresolved_issues": 0, "sla_breach_count": 0},
            "execution": {"overdue_tasks": 0, "health": "on_track"},
            "finance": {"total_overdue_cents": 0, "days_sales_outstanding": 30},
            "revenue": {"trend": "stable"},
            "team": {"departures_30d": 0},
        }
        result = run_startup_detector(healthy)
        assert result["alert_count"] == 0
        assert result["correlation_count"] == 0
        assert result["alerts"] == []
        assert result["correlations"] == []

    def test_unhealthy_state(self):
        unhealthy = {
            "support": {"unresolved_issues": 20, "sla_breach_count": 2},
            "execution": {"overdue_tasks": 10, "health": "blocked"},
            "finance": {"total_overdue_cents": 10_000_000, "days_sales_outstanding": 90},
            "revenue": {"trend": "declining"},
            "team": {"departures_30d": 5},
        }
        result = run_startup_detector(unhealthy)
        assert result["alert_count"] > 0
        assert result["correlation_count"] > 0

    def test_empty_state_graceful(self):
        result = run_startup_detector({})
        assert result["alert_count"] == 0
        assert result["correlation_count"] == 0

"""Unit tests for Startup Guardian watchlist functions."""
from src.guardian.startup_watchlists import run_watchlists


class TestRunWatchlists:
    def test_healthy_state_returns_empty(self):
        healthy = {
            "support": {"unresolved_issues": 1, "sla_breach_count": 0},
            "execution": {"overdue_tasks": 0, "health": "on_track"},
            "finance": {"total_overdue_cents": 1000, "days_sales_outstanding": 30},
            "revenue": {"trend": "stable"},
            "team": {"departures_30d": 0},
        }
        alerts = run_watchlists(healthy)
        assert alerts == []

    def test_unhealthy_state_returns_alerts(self):
        unhealthy = {
            "support": {"unresolved_issues": 20, "sla_breach_count": 3},
            "execution": {"overdue_tasks": 10, "health": "blocked"},
            "finance": {"total_overdue_cents": 10_000_000, "days_sales_outstanding": 90},
            "revenue": {"trend": "declining"},
            "team": {"departures_30d": 5},
        }
        alerts = run_watchlists(unhealthy)
        assert len(alerts) > 0
        ids = [a["id"] for a in alerts]
        assert "SG-SUP-01" in ids
        assert "SG-SUP-02" in ids
        assert "SG-EXE-01" in ids
        assert "SG-FIN-01" in ids
        assert "SG-REV-01" in ids
        assert "SG-TEAM-01" in ids

    def test_missing_keys_graceful(self):
        alerts = run_watchlists({})
        assert isinstance(alerts, list)
        assert len(alerts) == 0

    def test_empty_state_no_alerts(self):
        alerts = run_watchlists({
            "support": {}, "execution": {}, "finance": {}, "revenue": {}, "team": {},
        })
        assert alerts == []

"""Tests for Monthly Business Health Report - TDD Red phase."""
import pytest
from datetime import datetime


class TestBusinessHealthReportService:
    """Business health report generation and retrieval."""

    def setup_method(self):
        """Reset report state before each test."""
        from src.services.business_health_report import reset_report_store
        reset_report_store()

    def test_generate_report_creates_id(self):
        """Report generation creates unique report_id."""
        from src.services.business_health_report import generate_report
        report = generate_report("tenant-001", "2026-05")
        assert report.report_id != ""
        assert report.report_id.startswith("rpt_")

    def test_generate_report_auto_month(self):
        """If month is None, uses current month."""
        from src.services.business_health_report import generate_report
        report = generate_report("tenant-001", None)
        current_month = datetime.now().strftime("%Y-%m")
        assert report.report_month == current_month

    def test_get_latest_report_retrieves(self):
        """get_latest_report retrieves the most recent report."""
        from src.services.business_health_report import (
            generate_report,
            get_latest_report,
        )
        generate_report("tenant-001", "2026-04")
        latest = generate_report("tenant-001", "2026-05")
        result = get_latest_report("tenant-001")
        assert result is not None
        assert result.report_month == "2026-05"

    def test_get_report_history_sorted(self):
        """get_report_history returns sorted reports, newest first."""
        from src.services.business_health_report import (
            generate_report,
            get_report_history,
        )
        generate_report("tenant-001", "2026-01")
        generate_report("tenant-001", "2026-03")
        generate_report("tenant-001", "2026-02")
        history = get_report_history("tenant-001", limit=6)
        assert len(history) == 3
        assert history[0].report_month == "2026-03"
        assert history[1].report_month == "2026-02"
        assert history[2].report_month == "2026-01"

    def test_summarize_health_score_critical(self):
        """Health score returns Critical when unresolved_risks > 3."""
        from src.services.business_health_report import (
            MonthlyBusinessHealthReport,
            summarize_health_score,
        )
        report = MonthlyBusinessHealthReport(
            tenant_id="tenant-001",
            report_month="2026-05",
            total_alerts=10,
            unresolved_risks=["risk1", "risk2", "risk3", "risk4"],
        )
        score = summarize_health_score(report)
        assert score == "Critical"

    def test_summarize_health_score_at_risk(self):
        """Health score returns At-Risk when patterns > 5."""
        from src.services.business_health_report import (
            MonthlyBusinessHealthReport,
            summarize_health_score,
        )
        report = MonthlyBusinessHealthReport(
            tenant_id="tenant-001",
            report_month="2026-05",
            total_alerts=10,
            patterns_detected=["p1", "p2", "p3", "p4", "p5", "p6"],
            unresolved_risks=["risk1"],
        )
        score = summarize_health_score(report)
        assert score == "At-Risk"

    def test_summarize_health_score_stable(self):
        """Health score returns Stable otherwise."""
        from src.services.business_health_report import (
            MonthlyBusinessHealthReport,
            summarize_health_score,
        )
        report = MonthlyBusinessHealthReport(
            tenant_id="tenant-001",
            report_month="2026-05",
            total_alerts=5,
            patterns_detected=["p1", "p2"],
            unresolved_risks=["risk1"],
        )
        score = summarize_health_score(report)
        assert score == "Stable"

    def test_report_has_all_fields(self):
        """Generated report has all required fields with correct defaults."""
        from src.services.business_health_report import generate_report
        report = generate_report("tenant-001", "2026-05")
        assert report.tenant_id == "tenant-001"
        assert report.report_month == "2026-05"
        assert report.total_alerts == 0
        assert report.patterns_detected == []
        assert report.decisions_logged == 0
        assert report.unresolved_risks == []
        assert report.operating_trends == {}
        assert report.top_blindspots == []
        assert report.changes_since_last_month == []
        assert report.watch_intensity_changes == {}
        assert report.generated_at is not None
        assert report.report_id != ""
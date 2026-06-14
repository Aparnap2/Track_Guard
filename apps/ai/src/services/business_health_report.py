from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class MonthlyBusinessHealthReport:
    tenant_id: str
    report_month: str
    total_alerts: int = 0
    patterns_detected: list[str] = field(default_factory=list)
    decisions_logged: int = 0
    unresolved_risks: list[str] = field(default_factory=list)
    operating_trends: dict[str, float] = field(default_factory=dict)
    top_blindspots: list[str] = field(default_factory=list)
    changes_since_last_month: list[str] = field(default_factory=list)
    watch_intensity_changes: dict[str, str] = field(default_factory=dict)
    generated_at: datetime | None = None
    report_id: str = ""


_report_store: dict[str, list[MonthlyBusinessHealthReport]] = {}


def reset_report_store() -> None:
    """Reset the in-memory report store for testing."""
    global _report_store
    _report_store.clear()


def _get_tenant_reports(tenant_id: str) -> list[MonthlyBusinessHealthReport]:
    """Get or create the report list for a tenant."""
    if tenant_id not in _report_store:
        _report_store[tenant_id] = []
    return _report_store[tenant_id]


def generate_report(tenant_id: str, month: str | None = None) -> MonthlyBusinessHealthReport:
    """Generate a monthly business health report."""
    if month is None:
        month = datetime.now().strftime("%Y-%m")

    report = MonthlyBusinessHealthReport(
        tenant_id=tenant_id,
        report_month=month,
        generated_at=datetime.now(),
        report_id=f"rpt_{uuid.uuid4().hex[:12]}",
    )

    tenant_reports = _get_tenant_reports(tenant_id)
    tenant_reports.append(report)
    return report


def get_latest_report(tenant_id: str) -> MonthlyBusinessHealthReport | None:
    """Get the most recent report for a tenant."""
    tenant_reports = _get_tenant_reports(tenant_id)
    if not tenant_reports:
        return None
    return sorted(tenant_reports, key=lambda r: r.report_month, reverse=True)[0]


def get_report_history(tenant_id: str, limit: int = 6) -> list[MonthlyBusinessHealthReport]:
    """Get sorted report history for a tenant, newest first."""
    tenant_reports = _get_tenant_reports(tenant_id)
    sorted_reports = sorted(tenant_reports, key=lambda r: r.report_month, reverse=True)
    return sorted_reports[:limit]


def summarize_health_score(report: MonthlyBusinessHealthReport) -> str:
    """Summarize health score based on report metrics."""
    if len(report.unresolved_risks) > 3:
        return "Critical"
    if len(report.patterns_detected) > 5:
        return "At-Risk"
    return "Stable"
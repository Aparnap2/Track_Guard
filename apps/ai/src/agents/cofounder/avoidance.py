"""Avoidance Detection: Pattern-based founder avoidance detection.

Detects when founders avoid critical activities despite warning signs.
PRD Reference: Section 605-612
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class AvoidancePattern:
    name: str
    description: str
    detected: bool
    severity: str  # "critical" | "warning" | "info"
    evidence: list[str]
    recommendation: str


AVOIDANCE_PATTERNS = {
    "fundraising_deflection": {
        "condition": "founder_focus == 'fundraising' AND fundraising_activities < 2 AND runway_days < 180",
        "description": "Founder avoiding fundraising despite short runway",
        "severity": "critical",
        "recommendation": "Founder avoiding fundraising despite short runway",
    },
    "headcount_deflection": {
        "condition": "runway_days < 90 AND hiring_intent == 'freeze' AND burn_rate_trend == 'increasing'",
        "description": "Founder avoiding hiring despite burn rate increase",
        "severity": "critical",
        "recommendation": "Founder avoiding hiring despite burn rate increase",
    },
    "churn_avoidance": {
        "condition": "churn_rate > 0.10 AND customer_conversation_count < 1 AND last_customer_call_days > 14",
        "description": "Founder avoiding difficult customer conversations",
        "severity": "warning",
        "recommendation": "Founder avoiding difficult customer conversations",
    },
    "metric_avoidance": {
        "condition": "dashboard_views_7d < 3 AND (burn_alert OR churn_rate > 0.05)",
        "description": "Founder avoiding metric review during critical period",
        "severity": "warning",
        "recommendation": "Founder avoiding metric review during critical period",
    },
}


class AvoidanceDetectionService:
    """Avoidance pattern detection service."""

    def __init__(self) -> None:
        pass

    def detect(self, mission_state: dict) -> list[AvoidancePattern]:
        """Detect avoidance patterns from mission state dict.

        Args:
            mission_state: Dict with signal flags and metrics

        Returns:
            List of detected avoidance patterns
        """
        patterns = []

        # fundraising_deflection
        founder_focus = mission_state.get("founder_focus")
        fundraising_activities = mission_state.get("fundraising_activities", 0)
        runway_days = mission_state.get("runway_days", 999)
        if (
            founder_focus == "fundraising"
            and fundraising_activities < 2
            and runway_days < 180
        ):
            patterns.append(AvoidancePattern(
                name="fundraising_deflection",
                description=AVOIDANCE_PATTERNS["fundraising_deflection"]["description"],
                detected=True,
                severity=AVOIDANCE_PATTERNS["fundraising_deflection"]["severity"],
                evidence=[
                    f"founder_focus: {founder_focus}",
                    f"fundraising_activities: {fundraising_activities}",
                    f"runway_days: {runway_days}",
                ],
                recommendation=AVOIDANCE_PATTERNS["fundraising_deflection"]["recommendation"],
            ))

        # headcount_deflection
        hiring_intent = mission_state.get("hiring_intent")
        burn_rate_trend = mission_state.get("burn_rate_trend")
        if (
            runway_days < 90
            and hiring_intent == "freeze"
            and burn_rate_trend == "increasing"
        ):
            patterns.append(AvoidancePattern(
                name="headcount_deflection",
                description=AVOIDANCE_PATTERNS["headcount_deflection"]["description"],
                detected=True,
                severity=AVOIDANCE_PATTERNS["headcount_deflection"]["severity"],
                evidence=[
                    f"runway_days: {runway_days}",
                    f"hiring_intent: {hiring_intent}",
                    f"burn_rate_trend: {burn_rate_trend}",
                ],
                recommendation=AVOIDANCE_PATTERNS["headcount_deflection"]["recommendation"],
            ))

        # churn_avoidance
        churn_rate = mission_state.get("churn_rate", 0)
        customer_conversation_count = mission_state.get("customer_conversation_count", 0)
        last_customer_call_days = mission_state.get("last_customer_call_days", 0)
        if (
            churn_rate > 0.10
            and customer_conversation_count < 1
            and last_customer_call_days > 14
        ):
            patterns.append(AvoidancePattern(
                name="churn_avoidance",
                description=AVOIDANCE_PATTERNS["churn_avoidance"]["description"],
                detected=True,
                severity=AVOIDANCE_PATTERNS["churn_avoidance"]["severity"],
                evidence=[
                    f"churn_rate: {churn_rate}",
                    f"customer_conversation_count: {customer_conversation_count}",
                    f"last_customer_call_days: {last_customer_call_days}",
                ],
                recommendation=AVOIDANCE_PATTERNS["churn_avoidance"]["recommendation"],
            ))

        # metric_avoidance
        dashboard_views_7d = mission_state.get("dashboard_views_7d", 999)
        burn_alert = mission_state.get("burn_alert", False)
        if (
            dashboard_views_7d < 3
            and (burn_alert or churn_rate > 0.05)
        ):
            patterns.append(AvoidancePattern(
                name="metric_avoidance",
                description=AVOIDANCE_PATTERNS["metric_avoidance"]["description"],
                detected=True,
                severity=AVOIDANCE_PATTERNS["metric_avoidance"]["severity"],
                evidence=[
                    f"dashboard_views_7d: {dashboard_views_7d}",
                    f"burn_alert: {burn_alert}",
                    f"churn_rate: {churn_rate}",
                ],
                recommendation=AVOIDANCE_PATTERNS["metric_avoidance"]["recommendation"],
            ))

        return patterns

    def is_founder_avoiding(self, mission_state: dict) -> bool:
        """Return True if ANY avoidance pattern detected.

        Args:
            mission_state: Dict with signal flags and metrics

        Returns:
            True if any avoidance pattern detected
        """
        patterns = self.detect(mission_state)
        return len(patterns) > 0

    def get_critical_avoidances(self, mission_state: dict) -> list[AvoidancePattern]:
        """Return only critical severity patterns.

        Args:
            mission_state: Dict with signal flags and metrics

        Returns:
            List of critical severity avoidance patterns
        """
        patterns = self.detect(mission_state)
        return [p for p in patterns if p.severity == "critical"]


def detect_avoidances(mission_state: dict) -> list[AvoidancePattern]:
    """Convenience function for avoidance detection.

    Args:
        mission_state: Dict with signal flags and metrics

    Returns:
        List of detected avoidance patterns
    """
    service = AvoidanceDetectionService()
    return service.detect(mission_state)
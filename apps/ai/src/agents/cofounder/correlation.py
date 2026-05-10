"""Correlation: Cross-signal detection + synthesis.

Detects co-signals across domains and synthesizes insights.
PRD Reference: Section 597-604
"""
from dataclasses import dataclass
from typing import Optional

from src.session.mission_state import MissionState


# Co-signal detection rules per PRD
CO_SIGNALS = {
    "burn_spike_plus_churn": {
        "condition": "burn_alert AND churn_rate > 0.05",
        "description": "Burn spike coinciding with churn",
    },
    "error_spike_plus_churn_risk": {
        "condition": "error_spike AND churn_risk_users > 2",
        "description": "Error spike with high-risk users",
    },
    "short_runway_fundraising": {
        "condition": "runway_days < 180 AND founder_focus == 'fundraising'",
        "description": "Short runway during fundraising focus",
    },
}


@dataclass
class CoSignal:
    name: str
    description: str
    severity: str  # "critical" | "warning" | "info"


class CorrelationAgent:
    """Cross-signal detection agent."""
    
    def __init__(self):
        pass
    
    def detect(
        self,
        mission_state: Optional[MissionState] = None,
    ) -> list[CoSignal]:
        """Detect co-signals from MissionState.
        
        Args:
            mission_state: Current MissionState
            
        Returns:
            List of detected co-signals (empty if none)
        """
        if mission_state is None:
            return []
        
        signals = []
        
        # Check burn_spike_plus_churn
        if mission_state.burn_alert and mission_state.churn_rate:
            if mission_state.churn_rate > 0.05:
                signals.append(CoSignal(
                    name="burn_spike_plus_churn",
                    description=CO_SIGNALS["burn_spike_plus_churn"]["description"],
                    severity="critical",
                ))
        
        # Check error_spike_plus_churn_risk
        if mission_state.error_spike and mission_state.churn_risk_users > 2:
            signals.append(CoSignal(
                name="error_spike_plus_churn_risk",
                description=CO_SIGNALS["error_spike_plus_churn_risk"]["description"],
                severity="warning",
            ))
        
        # Check short_runway_fundraising
        if mission_state.runway_days and mission_state.founder_focus:
            if mission_state.runway_days < 180 and mission_state.founder_focus == "fundraising":
                signals.append(CoSignal(
                    name="short_runway_fundraising",
                    description=CO_SIGNALS["short_runway_fundraising"]["description"],
                    severity="critical",
                ))
        
        return signals
    
    def should_synthesize(
        self,
        mission_state: Optional[MissionState] = None,
    ) -> bool:
        """Determine if synthesis message is warranted.
        
        Per PRD: ONE synthesis message per day maximum.
        
        Args:
            mission_state: Current MissionState
            
        Returns:
            True if synthesis should run
        """
        signals = self.detect(mission_state)
        return len(signals) > 0


def detect_correlation(
    mission_state: Optional[MissionState] = None,
) -> list[CoSignal]:
    """Convenience function for correlation detection."""
    agent = CorrelationAgent()
    return agent.detect(mission_state)
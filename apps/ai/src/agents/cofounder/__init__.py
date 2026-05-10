"""Co-founder Agent for Sarthi V3.0.

This module provides the manager layer that orchestrates Employee Agents:
- router.py: routes messages to employee agents
- reflector.py: reads founder response, converts to score
- curator.py: updates Graphiti playbook
- correlation.py: cross-signal detection + synthesis

PRD Reference: Section 789-793, 220-261
"""
from .router import Router, route_message
from .reflector import Reflector, score_founder_response
from .curator import Curator, update_playbook
from .correlation import CorrelationAgent, detect_correlation

__all__ = [
    "Router",
    "route_message",
    "Reflector",
    "score_founder_response",
    "Curator",
    "update_playbook",
    "CorrelationAgent",
    "detect_correlation",
]
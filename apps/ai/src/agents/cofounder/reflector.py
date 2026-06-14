"""Reflector: ACE Reflector for founder response scoring.

Converts founder responses into confidence scores for playbook updates.
PRD Reference: Section 249-257

V3.0: Wire Slack button feedback to Trust Battery scoring.
"""
import logging
import os
from dataclasses import dataclass
from enum import Enum


class ResponseType(Enum):
    """Founder response types."""
    ACKNOWLEDGED = "acknowledged"
    ACTED_ON = "acted_on"
    IGNORED = "ignored"
    DISPUTED = "disputed"
    DISMISSED = "dismissed"


# Score weights per PRD Section 252
RESPONSE_SCORES = {
    ResponseType.ACKNOWLEDGED: 1.0,
    ResponseType.ACTED_ON: 1.5,
    ResponseType.IGNORED: -0.5,
    ResponseType.DISPUTED: -0.5,
    ResponseType.DISMISSED: -1.5,
}


@dataclass
class Reflection:
    response_type: ResponseType
    score: float
    domain: str  # "finance" | "bi" | "ops"


class Reflector:
    """ACE Reflector: converts founder response to score."""
    
    def __init__(self):
        pass
    
    def score(self, response: str, domain: str) -> Reflection:
        """Score founder response.
        
        Args:
            response: Founder's response text or action
            domain: Domain (finance/bi/ops)
            
        Returns:
            Reflection with score
        """
        # Handle empty feedback as neutral (no penalty)
        if not response or not response.strip():
            return Reflection(
                response_type=ResponseType.IGNORED,
                score=0.0,
                domain=domain,
            )
        
        # Determine response type from text
        response_lower = response.lower()
        
        # Check DISPUTED - "already knew" before ACTED_ON
        if any(kw in response_lower for kw in ["already knew", "knew about", "knew this", "disagree", "wrong", "not right", "incorrect"]):
            return self._build_reflection(ResponseType.DISPUTED, domain)
        
        # Check ACTED_ON
        if any(kw in response_lower for kw in ["acted", "doing", "done", "took action"]):
            return self._build_reflection(ResponseType.ACTED_ON, domain)
        
        # Check DISMISSED
        if any(kw in response_lower for kw in ["dismiss", "ignore", "not relevant"]):
            return self._build_reflection(ResponseType.DISMISSED, domain)
        
        # Check ACKNOWLEDGED
        if any(kw in response_lower for kw in ["ok", "thanks", "got it", "understood", "seen"]):
            return self._build_reflection(ResponseType.ACKNOWLEDGED, domain)
        
        # Default: assumed ignored after timeout
        return self._build_reflection(ResponseType.IGNORED, domain)
    
    def _build_reflection(self, response_type: ResponseType, domain: str) -> Reflection:
        return Reflection(
            response_type=response_type,
            score=RESPONSE_SCORES[response_type],
            domain=domain,
        )


def score_founder_response(response: str, domain: str) -> Reflection:
    """Convenience function for scoring."""
    reflector = Reflector()
    return reflector.score(response, domain)


# Mapping from Slack button response types to Trust Battery event types
BUTTON_TO_TRUST_EVENT = {
    "acknowledged": "rate_good",
    "rate_good": "rate_good",
    "disputed": "dispute",
    "dispute": "dispute",
    "rate_bad": "rate_bad",
}

# Map alert ID prefix to domain and agent name
ALERT_PREFIX_MAP = {
    "FG": ("finance", "Finance Guardian"),
    "BG": ("bi", "BI Analyst"),
    "OG": ("ops", "Ops Watch"),
}


def score_from_button(alert_id: str, response_type: str, score: float) -> None:
    """Score feedback from Slack button interaction.

    V3.0: Wires button feedback to Trust Battery scoring.
    Maps button types to trust score deltas and persists to DB.

    Delta mapping (per Arthashastra audit):
    - rate_good:  trust_score += 0.05 (max 0.95)
    - rate_bad:   trust_score -= 0.10 (min 0.05)
    - dispute:    trust_score -= 0.20 (min 0.05)

    Args:
        alert_id: The alert/decision being scored (e.g., "FG-001")
        response_type: Response type (acknowledged, rate_good, rate_bad, dispute, disputed)
        score: Feedback score (+1.0 or -1.0)
    """
    log = logging.getLogger(__name__)
    log.info(
        "Button feedback received",
        extra={
            "alert_id": alert_id,
            "response_type": response_type,
            "score": score,
        },
    )

    # Map response_type to trust event type
    event_type = BUTTON_TO_TRUST_EVENT.get(response_type)
    if not event_type:
        log.warning("Unknown button response type", extra={"response_type": response_type})
        return

    # Extract domain and agent_name from alert_id prefix
    prefix = alert_id.split("-")[0] if "-" in alert_id else ""
    domain_info = ALERT_PREFIX_MAP.get(prefix)
    if not domain_info:
        log.warning(
            "Could not determine agent from alert_id",
            extra={"alert_id": alert_id, "prefix": prefix},
        )
        return

    domain, agent_name = domain_info
    tenant_id = os.environ.get("DEFAULT_TENANT_ID", "default")

    # Step 1: Update in-memory trust score
    from src.services.trust_battery import update_trust_score
    profile = update_trust_score(tenant_id, agent_name, event_type)

    log.info(
        "Trust score updated from button feedback",
        extra={
            "agent": agent_name,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "trust_score_after": profile.trust_score,
        },
    )

    # Step 2: Persist event to DB (fire-and-forget, best-effort)
    try:
        import asyncio
        from src.services.trust_battery_db import log_trust_event

        event_data = {
            "alert_id": alert_id,
            "button_score": score,
            "trust_score_after": profile.trust_score,
            "route_priority_after": profile.route_priority,
        }

        asyncio.run(log_trust_event(tenant_id, agent_name, event_type, event_data))
    except Exception:
        log.debug("DB trust event logging unavailable (non-blocking)", exc_info=True)
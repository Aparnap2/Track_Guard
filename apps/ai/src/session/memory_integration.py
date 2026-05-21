"""
Session Memory Integration — Graphiti write triggers.

Per PRD V3.0:
- Only trigger Graphiti writes on specific events:
  - alert_fired: Finance Guardian triggered an alert
  - founder_ack: Founder acknowledged an agent response
  - founder_disputed: Founder disputed an agent response
  - decision_logged: Strategic decision was made
  - intent_detected: Founder intent was detected

This module provides:
- SessionMemoryWriter: Write sessions as Graphiti episodes
- should_write_to_graphiti(): Check if event triggers Graphiti write
- search_session_memory(): Search past sessions via Graphiti
"""
from __future__ import annotations

import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

# Per PRD: Only these events trigger Graphiti writes
GRAPHITI_WRITE_TRIGGERS = frozenset({
    "alert_fired",
    "founder_ack",
    "founder_disputed",
    "decision_logged",
    "intent_detected",
})


def should_write_to_graphiti(event_type: str) -> bool:
    """Check if event type should trigger Graphiti write.

    Per PRD V3.0: Only specific events trigger Graphiti writes.

    Args:
        event_type: The event type to check

    Returns:
        True if event triggers Graphiti write
    """
    return event_type in GRAPHITI_WRITE_TRIGGERS


class SessionMemoryWriter:
    """Write session events to Graphiti semantic memory.

    Per PRD V3.0:
    - Writes episodes only on triggered events
    - Falls back gracefully if Graphiti is down

    Attributes:
        tenant_id: Tenant for isolation
        _semantic_memory: Lazy-loaded SemanticMemory instance
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._semantic_memory = None

    def _get_semantic_memory(self):
        """Lazy load SemanticMemory to avoid import errors."""
        if self._semantic_memory is None:
            try:
                from src.memory.semantic import SemanticMemory
                self._semantic_memory = SemanticMemory(tenant_id=self.tenant_id)
            except ImportError as e:
                log.warning(f"Failed to import SemanticMemory: {e}")
                return None
        return self._semantic_memory

    def write_message_as_episode(
        self,
        content: str,
        event_type: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Write session message as Graphiti episode.

        Only writes if event_type is in GRAPHITI_WRITE_TRIGGERS.

        Args:
            content: Message content to write
            event_type: Event type (alert_fired, founder_ack, etc.)
            metadata: Optional metadata dict

        Returns:
            True if written successfully, False if skipped or failed
        """
        # Per PRD: Only trigger on specific events
        if not should_write_to_graphiti(event_type):
            log.debug(f"Skipping Graphiti write for event_type: {event_type}")
            return False

        sm = self._get_semantic_memory()
        if sm is None:
            log.warning("SemanticMemory not available, skipping Graphiti write")
            return False

        # Check if Graphiti is available
        if not sm.available():
            log.warning("Graphiti not available, skipping write (fallback contract)")
            return False

        # Format episode body
        episode_body = self._format_episode_body(content, event_type, metadata)
        episode_name = f"session:{event_type}:{self.tenant_id}"

        try:
            result = sm.write_episode(episode_name, episode_body)
            if result:
                log.info(f"Wrote session episode to Graphiti: {event_type}")
            return result
        except Exception as e:
            log.error(f"Failed to write session episode: {e}")
            return False

    def _format_episode_body(
        self,
        content: str,
        event_type: str,
        metadata: Optional[dict],
    ) -> str:
        """Format episode body for Graphiti as JSON.

        JSON format per Anthropic talk finding: models are far less likely
        to overwrite JSON than Markdown. All fields at top level.

        Args:
            content: Message content
            event_type: Event type
            metadata: Optional metadata

        Returns:
            JSON-formatted episode body string
        """
        import json
        from datetime import datetime, timezone

        body = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content": content,
        }

        if metadata:
            body.update(metadata)

        body["format"] = "session_episode_v1"

        return json.dumps(body)

    def write_alert_fired(
        self,
        alert_id: str,
        alert_type: str,
        message: str,
    ) -> bool:
        """Write alert_fired event to Graphiti.

        Args:
            alert_id: Alert identifier
            alert_type: Type of alert (FG-, BG-, OG-)
            message: Alert message

        Returns:
            True if written successfully
        """
        return self.write_message_as_episode(
            content=f"[{alert_id}] {alert_type}: {message}",
            event_type="alert_fired",
            metadata={"alert_id": alert_id, "alert_type": alert_type},
        )

    def write_founder_ack(
        self,
        agent_name: str,
        message: str,
    ) -> bool:
        """Write founder_ack event to Graphiti.

        Args:
            agent_name: Agent that was acknowledged
            message: Ack message

        Returns:
            True if written successfully
        """
        return self.write_message_as_episode(
            content=f"Founder acknowledged {agent_name}: {message}",
            event_type="founder_ack",
            metadata={"agent_name": agent_name},
        )

    def write_founder_dispute(
        self,
        agent_name: str,
        message: str,
    ) -> bool:
        """Write founder_disputed event to Graphiti.

        Args:
            agent_name: Agent that was disputed
            message: Dispute message

        Returns:
            True if written successfully
        """
        return self.write_message_as_episode(
            content=f"Founder disputed {agent_name}: {message}",
            event_type="founder_disputed",
            metadata={"agent_name": agent_name},
        )

    def write_decision_logged(
        self,
        decision: str,
        context: Optional[dict] = None,
    ) -> bool:
        """Write decision_logged event to Graphiti.

        Args:
            decision: Decision text
            context: Optional decision context

        Returns:
            True if written successfully
        """
        return self.write_message_as_episode(
            content=f"Strategic decision: {decision}",
            event_type="decision_logged",
            metadata=context,
        )

    def write_intent_detected(
        self,
        intent: str,
        confidence: float,
    ) -> bool:
        """Write intent_detected event to Graphiti.

        Args:
            intent: Detected intent
            confidence: Intent confidence score

        Returns:
            True if written successfully
        """
        return self.write_message_as_episode(
            content=f"Intent detected: {intent} (confidence: {confidence})",
            event_type="intent_detected",
            metadata={"intent": intent, "confidence": confidence},
        )


def search_session_memory(
    tenant_id: str,
    query: str,
    num_results: int = 5,
) -> list[dict]:
    """Search past sessions via Graphiti.

    Per PRD V3.0: Semantic search over session history.

    Args:
        tenant_id: Tenant for isolation
        query: Natural language search query
        num_results: Maximum number of results

    Returns:
        List of search results as dicts. Empty list on failure (fallback contract).
    """
    try:
        from src.memory.semantic import SemanticMemory

        sm = SemanticMemory(tenant_id=tenant_id)
        if not sm.available():
            log.warning("Graphiti not available for search (fallback contract)")
            return []

        return sm.search(query, num_results=num_results)
    except ImportError:
        log.warning("SemanticMemory not available")
        return []
    except Exception as e:
        log.error(f"Session memory search failed: {e}")
        return []


# Convenience function for testing
def create_session_writer(tenant_id: str) -> SessionMemoryWriter:
    """Create a SessionMemoryWriter for the given tenant.

    Args:
        tenant_id: Tenant ID

    Returns:
        SessionMemoryWriter instance
    """
    return SessionMemoryWriter(tenant_id=tenant_id)
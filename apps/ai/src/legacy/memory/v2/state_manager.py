"""Agent State Manager — per-tenant belief state."""
from __future__ import annotations
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class AgentStateManager:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.key = f"state:{tenant_id}"
        self._store = {}

    def get_beliefs(self) -> dict:
        return self._store.get(self.key, self._default_state())

    def update_belief(self, topic: str, value: str, confidence: float, source: str):
        state = self.get_beliefs()
        state["beliefs"][topic] = {
            "value": value, "confidence": confidence,
            "source": source, "updated_at": now_iso(),
        }
        self._store[self.key] = state

    def get_uncertainties(self) -> list[dict]:
        state = self.get_beliefs()
        return [
            {"topic": k, **v} for k, v in state["beliefs"].items()
            if v["confidence"] < 0.4
        ]

    def _default_state(self) -> dict:
        return {
            "beliefs": {
                "founder_archetype": {
                    "value": "unknown", "confidence": 0.0, "source": "default",
                }
            },
            "watches": [],
            "autonomy_slider": {
                "warning_anomaly": "auto",
                "critical_anomaly": "hitl",
                "investor_update": "hitl",
            },
        }

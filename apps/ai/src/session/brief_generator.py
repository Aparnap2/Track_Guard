"""Brief generator — 2-sentence plain-English business summary after MissionState updates."""
from __future__ import annotations

import logging
from src.config.llm import chat_completion
from src.session.mission_state import get_mission_state, update_mission_state, MissionState

log = logging.getLogger(__name__)

_BRIEF_TEMPLATE = (
    "Write 2 plain-English sentences summarising this business state. "
    "Runway: {runway_days}d | Burn alert: {burn_alert} | "
    "Churn rate: {churn_rate} | Active alerts: {active_alerts} | "
    "MRR trend: {mrr_trend} | Trust score: {trust_score}. "
    "No jargon. Founder reads this first thing. Be direct."
)

async def generate_prepared_brief(tenant_id: str) -> str | None:
    """Load MissionState, generate 2-sentence brief, persist it, return it."""
    state = await get_mission_state(tenant_id)
    prompt = _BRIEF_TEMPLATE.format(
        runway_days=state.runway_days or "?",
        burn_alert=state.burn_alert,
        churn_rate=state.churn_rate or "?",
        active_alerts=state.active_alerts or "none",
        mrr_trend=state.mrr_trend or "?",
        trust_score=state.trust_score or "?",
    )
    try:
        # chat_completion is synchronous
        brief = chat_completion(
            messages=[
                {"role": "system", "content": "You are a concise business briefing assistant. Output exactly 2 sentences. No preamble."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=80,
            temperature=0.3,
        )
        if not brief:
            log.warning("Empty brief returned for tenant %s", tenant_id)
            return None
        state.prepared_brief = brief.strip()
        state.last_updated_by = "brief_generator"
        await update_mission_state(state, generate_brief=False)
        log.info("Prepared brief generated for tenant %s: %s", tenant_id, brief[:80])
        return brief.strip()
    except Exception:
        log.exception("Failed to generate prepared brief for tenant %s", tenant_id)
        return None

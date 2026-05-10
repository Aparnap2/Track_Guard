"""
HiringAgent Node Functions.

Each node:
  - Accepts state: HiringState
  - Returns dict of only fields it changes
  - Never raises — errors written to state["error"] + state["error_node"]
  - Uses try/except with logging
"""
from __future__ import annotations
import logging
from typing import Any

from src.agents.hiring.state import HiringState
from src.agents.hiring.prompts import candidate_scorer, pipeline_decider

logger = logging.getLogger(__name__)


def load_candidate(state: HiringState) -> dict:
    """
    Load candidate data from input.

    Populates:
      - name, email, resume_url, source
      - role_id, candidate_data
    """
    result: dict = {}

    candidate_data = state.get("candidate_data", {})

    result["name"] = candidate_data.get("name", "")
    result["email"] = candidate_data.get("email", "")
    result["resume_url"] = candidate_data.get("resume_url", "")
    result["source"] = candidate_data.get("source", "manual")
    result["role_id"] = state.get("role_id", candidate_data.get("role_id"))

    if not result["name"] or not result["email"]:
        result["error"] = "name and email are required"
        result["error_node"] = "load_candidate"

    return result


def fetch_role_requirements(state: HiringState) -> dict:
    """
    Fetch role requirements from database.

    Populates:
      - role_title, role_description, role_requirements
    """
    result: dict = {
        "role_title": "",
        "role_description": "",
        "role_requirements": "",
    }

    role_id = state.get("role_id")
    if not role_id:
        result["role_title"] = "General Position"
        result["role_requirements"] = "No specific requirements"
        return result

    try:
        from src.db.hiring import get_roles

        tenant_id = state.get("tenant_id", "unknown")
        roles = get_roles(tenant_id)

        for role in roles:
            if role.get("id") == role_id:
                result["role_title"] = role.get("title", "")
                result["role_description"] = role.get("description", "")
                result["role_requirements"] = role.get("requirements", "")
                break

    except Exception as e:
        logger.warning(f"Failed to fetch role requirements: {e}")
        result["role_requirements"] = "Standard hiring requirements"

    return result


def score_candidate(state: HiringState) -> dict:
    """
    Score candidate using DSPy CandidateScorer.

    Populates:
      - score_overall, score_technical
      - culture_signals, red_flags
      - recommended_action
    """
    result: dict = {}

    try:
        name = state.get("name", "Candidate")
        resume_text = state.get("candidate_data", {}).get("resume_text", "No resume provided")
        role_title = state.get("role_title", "Position")
        role_requirements = state.get("role_requirements", "Standard requirements")

        response = candidate_scorer(
            candidate_name=name,
            resume_text=resume_text[:2000],  # Limit for token budget
            role_title=role_title,
            role_requirements=role_requirements[:500],
        )

        # Parse scores
        try:
            result["score_overall"] = float(response.get("overall_score", 50))
        except (ValueError, TypeError):
            result["score_overall"] = 50.0

        try:
            result["score_technical"] = float(response.get("technical_score", 50))
        except (ValueError, TypeError):
            result["score_technical"] = 50.0

        # Parse signals and flags
        culture_signals_str = str(response.get("culture_signals", ""))
        result["culture_signals"] = [
            s.strip() for s in culture_signals_str.split(",") if s.strip() and s.strip() != "none"
        ]

        red_flags_str = str(response.get("red_flags", ""))
        result["red_flags"] = [
            f.strip() for f in red_flags_str.split(",") if f.strip() and f.strip() != "none"
        ]

        recommendation = str(response.get("recommendation", "hold")).lower()
        result["recommended_action"] = recommendation

        # Map recommendation to status
        status_map = {
            "advance_to_screening": "screening",
            "advance_to_interview": "interview",
            "reject": "rejected",
            "hold": "new",
        }
        result["status"] = status_map.get(recommendation, "new")

        logger.info(f"Scored candidate {name}: overall={result['score_overall']}, action={result['recommended_action']}")

    except Exception as e:
        logger.error(f"Candidate scoring failed: {e}")
        result["score_overall"] = 50.0
        result["score_technical"] = 50.0
        result["culture_signals"] = []
        result["red_flags"] = []
        result["recommended_action"] = "hold"
        result["status"] = "new"
        result["error"] = str(e)
        result["error_node"] = "score_candidate"

    return result


def update_pipeline(state: HiringState) -> dict:
    """
    Update candidate status in database and determine current stage.

    Populates:
      - current_stage
    """
    result: dict = {}

    try:
        from src.db.hiring import create_candidate, update_candidate_score

        tenant_id = state.get("tenant_id", "unknown")
        role_id = state.get("role_id")
        name = state.get("name", "")
        email = state.get("email", "")
        resume_url = state.get("resume_url", "")
        source = state.get("source", "manual")
        status = state.get("status", "new")

        # Create candidate if not exists (would need to check first in production)
        # For now, assume we're updating an existing candidate
        if role_id and name and email:
            # Try to update existing candidate
            update_candidate_score(
                candidate_id=0,  # Would be looked up by email
                score_overall=state.get("score_overall"),
                score_technical=state.get("score_technical"),
                culture_signals=state.get("culture_signals"),
                red_flags=state.get("red_flags"),
                recommended_action=state.get("recommended_action"),
                status=status,
            )

        result["current_stage"] = status
        logger.info(f"Updated pipeline for {name}: stage={status}")

    except Exception as e:
        logger.warning(f"Pipeline update failed: {e}")
        result["current_stage"] = state.get("status", "new")

    return result


def generate_recommendation(state: HiringState) -> dict:
    """
    Generate human-readable recommendation.

    Populates:
      - recommendation_text (for Slack/notification)
    """
    result: dict = {
        "recommendation_text": "",
    }

    try:
        name = state.get("name", "Candidate")
        score = state.get("score_overall", 0)
        action = state.get("recommended_action", "hold")
        red_flags = state.get("red_flags", [])

        action_text = {
            "advance_to_screening": "Advance to screening",
            "advance_to_interview": "Schedule interview",
            "reject": "Not a fit",
            "hold": "Put on hold",
        }.get(action, "Review manually")

        text = f"📋 *Candidate: {name}*\n"
        text += f"Score: {score:.0f}/100\n"
        text += f"Recommendation: {action_text}\n"

        if red_flags:
            text += f"⚠️ Flags: {', '.join(red_flags[:2])}"

        result["recommendation_text"] = text

    except Exception as e:
        logger.warning(f"Recommendation generation failed: {e}")
        result["recommendation_text"] = f"Candidate: {state.get('name', 'Unknown')}"

    return result
"""
LangGraph workflow for HiringAgent.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from src.agents.hiring.state import HiringState
from src.agents.hiring.nodes import (
    load_candidate,
    fetch_role_requirements,
    score_candidate,
    update_pipeline,
    generate_recommendation,
)


def create_hiring_graph() -> StateGraph:
    """
    Create the Hiring LangGraph.

    Nodes:
      - load_candidate: Load candidate data
      - fetch_role_requirements: Get role requirements
      - score_candidate: Score candidate using DSPy
      - update_pipeline: Update candidate status in DB
      - generate_recommendation: Generate human-readable recommendation

    Edges:
      - START -> load_candidate -> fetch_role_requirements -> score_candidate -> update_pipeline -> generate_recommendation -> END
    """
    graph = StateGraph(HiringState)

    # Add nodes
    graph.add_node("load_candidate", load_candidate)
    graph.add_node("fetch_role_requirements", fetch_role_requirements)
    graph.add_node("score_candidate", score_candidate)
    graph.add_node("update_pipeline", update_pipeline)
    graph.add_node("generate_recommendation", generate_recommendation)

    # Set entry point
    graph.set_entry_point("load_candidate")

    # Add edges
    graph.add_edge("load_candidate", "fetch_role_requirements")
    graph.add_edge("fetch_role_requirements", "score_candidate")
    graph.add_edge("score_candidate", "update_pipeline")
    graph.add_edge("update_pipeline", "generate_recommendation")
    graph.add_edge("generate_recommendation", END)

    return graph.compile()


# Default graph instance
hiring_graph = create_hiring_graph()


async def run_hiring_agent(tenant_id: str, candidate_data: dict, role_id: int = None) -> dict:
    """
    Run the HiringAgent to score a candidate.

    Args:
        tenant_id: Tenant identifier
        candidate_data: Dict with candidate info
        role_id: Optional role ID they're applying for

    Returns:
        dict with scores, recommendation, and recommendation_text
    """
    initial_state: HiringState = {
        "tenant_id": tenant_id,
        "candidate_data": candidate_data,
        "role_id": role_id,
        "name": "",
        "email": "",
        "resume_url": "",
        "source": "",
        "score_overall": 0.0,
        "score_technical": 0.0,
        "culture_signals": [],
        "red_flags": [],
        "recommended_action": "",
        "status": "new",
        "current_stage": "",
    }

    result = await hiring_graph.ainvoke(initial_state)

    return {
        "ok": True,
        "tenant_id": tenant_id,
        "name": result.get("name", ""),
        "email": result.get("email", ""),
        "score_overall": result.get("score_overall", 0),
        "score_technical": result.get("score_technical", 0),
        "culture_signals": result.get("culture_signals", []),
        "red_flags": result.get("red_flags", []),
        "recommended_action": result.get("recommended_action", ""),
        "status": result.get("status", "new"),
        "recommendation_text": result.get("recommendation_text", ""),
    }
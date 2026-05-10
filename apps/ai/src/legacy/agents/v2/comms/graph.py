"""
LangGraph workflow for CommsTriageAgent.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from src.agents.comms.state import CommsTriageState
from src.agents.comms.nodes import (
    fetch_messages,
    classify_messages,
    generate_digest,
    build_slack_message,
)


def create_comms_triage_graph() -> StateGraph:
    """
    Create the CommsTriage LangGraph.

    Nodes:
      - fetch_messages: Fetch messages from Slack channels
      - classify_messages: Classify each message
      - generate_digest: Generate daily digest
      - build_slack_message: Build Slack message

    Edges:
      - START -> fetch_messages -> classify_messages -> generate_digest -> build_slack_message -> END
    """
    graph = StateGraph(CommsTriageState)

    # Add nodes
    graph.add_node("fetch_messages", fetch_messages)
    graph.add_node("classify_messages", classify_messages)
    graph.add_node("generate_digest", generate_digest)
    graph.add_node("build_slack_message", build_slack_message)

    # Set entry point
    graph.set_entry_point("fetch_messages")

    # Add edges
    graph.add_edge("fetch_messages", "classify_messages")
    graph.add_edge("classify_messages", "generate_digest")
    graph.add_edge("generate_digest", "build_slack_message")
    graph.add_edge("build_slack_message", END)

    return graph.compile()


# Default graph instance
comms_triage_graph = create_comms_triage_graph()


async def run_comms_triage(tenant_id: str, channels: list[str]) -> dict:
    """
    Run the CommsTriage agent.

    Args:
        tenant_id: Tenant identifier
        channels: List of Slack channel names to triage

    Returns:
        dict with digest, slack_blocks, classified message counts
    """
    initial_state: CommsTriageState = {
        "tenant_id": tenant_id,
        "channels": channels,
        "messages": [],
        "classified_messages": [],
        "urgent_messages": [],
        "action_items": [],
        "digest": "",
        "slack_blocks": [],
        "data_sources": [],
    }

    result = await comms_triage_graph.ainvoke(initial_state)

    return {
        "ok": True,
        "tenant_id": tenant_id,
        "digest": result.get("digest", ""),
        "slack_blocks": result.get("slack_blocks", []),
        "total_messages": len(result.get("classified_messages", [])),
        "urgent_count": len(result.get("urgent_messages", [])),
        "action_count": len(result.get("action_items", [])),
    }
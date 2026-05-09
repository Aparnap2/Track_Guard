"""
LangGraph compilation for InvestorAgent.

Graph topology (with critic loop, max 1 iteration):
  fetch_metrics → retrieve_memory → generate_draft →
  critique_draft ──PASS / iter≥1──→ build_slack_message → send_slack → END
                 └────FAIL────────→ generate_draft (revise once)
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agents.investor.state import InvestorState
from src.agents.investor.nodes import (
    fetch_metrics,
    retrieve_memory,
    generate_draft,
    critique_draft,
    build_slack_message,
    send_slack,
)


def build_investor_graph():
    """
    Build and compile the InvestorAgent LangGraph with a self-reflection critic loop.

    The critic loop allows at most 1 revision:
      - If critique PASS or iteration >= 1 → proceed to output
      - If critique FAIL and iteration == 0 → loop back to generate_draft

    Returns:
        Compiled StateGraph ready for invocation
    """
    graph = StateGraph(InvestorState)

    # Add nodes
    graph.add_node("fetch_metrics",       fetch_metrics)
    graph.add_node("retrieve_memory",     retrieve_memory)
    graph.add_node("generate_draft",      generate_draft)
    graph.add_node("critique_draft",      critique_draft)
    graph.add_node("build_slack_message", build_slack_message)
    graph.add_node("send_slack",          send_slack)

    # Sequential edges up to critique
    graph.set_entry_point("fetch_metrics")
    graph.add_edge("fetch_metrics",   "retrieve_memory")
    graph.add_edge("retrieve_memory", "generate_draft")
    graph.add_edge("generate_draft",  "critique_draft")

    # Conditional: PASS or iteration>=1 → output, else loop back
    def critic_route(state):
        if state.get("quality_pass") or state.get("iteration", 0) >= 1:
            return "output"
        return "revise"

    graph.add_conditional_edges("critique_draft", critic_route, {
        "output": "build_slack_message",
        "revise": "generate_draft",
    })

    # Output path
    graph.add_edge("build_slack_message", "send_slack")
    graph.add_edge("send_slack",          END)

    return graph.compile()


# Module-level compiled graph (importable by Temporal activities)
investor_graph = build_investor_graph()

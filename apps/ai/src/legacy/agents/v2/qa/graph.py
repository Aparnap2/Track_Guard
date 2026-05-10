"""
LangGraph compilation for QAAgent.

Two agent patterns are exported:

1. qa_graph (backward-compatible):
   Sequential graph: match_question → fetch_data → retrieve_memory →
                     generate_answer → send_slack → END

2. qa_agent (Safe ReAct pattern):
   LLM + tools (search_pulse_memory, query_stripe_metrics, query_product_db)
   with safety guards: max calls, timeout, loop detection, cost ceiling
"""
from __future__ import annotations
import hashlib
import time

from langgraph.graph import StateGraph, END

from src.agents.qa.state import QAState
from src.agents.qa.nodes import (
    match_question,
    fetch_data,
    retrieve_memory,
    generate_answer,
    send_slack,
    QA_TOOLS,
)
from src.agents.qa.prompts import REACT_SYSTEM_PROMPT


# =============================================================================
# Backward-compatible sequential graph
# =============================================================================

def build_qa_graph() -> StateGraph:
    graph = StateGraph(QAState)

    # Add nodes
    graph.add_node("match_question",    match_question)
    graph.add_node("fetch_data",        fetch_data)
    graph.add_node("retrieve_memory",   retrieve_memory)
    graph.add_node("generate_answer",   generate_answer)
    graph.add_node("send_slack",        send_slack)

    # Sequential edges
    graph.set_entry_point("match_question")
    graph.add_edge("match_question",    "fetch_data")
    graph.add_edge("fetch_data",        "retrieve_memory")
    graph.add_edge("retrieve_memory",   "generate_answer")
    graph.add_edge("generate_answer",   "send_slack")
    graph.add_edge("send_slack",        END)

    return graph.compile()


# Module-level compiled graph (backward-compatible)
qa_graph = build_qa_graph()


# =============================================================================
# ReAct agent via create_react_agent
# =============================================================================

class SafeReActAgent:
    """ReAct agent with safety guards against infinite loops and excessive costs."""

    MAX_TOOL_CALLS = 5
    MAX_WALL_TIME = 30  # seconds
    MAX_COST = 0.50     # dollars

    def __init__(self):
        from src.config.llm import get_llm_client, get_chat_model
        self.llm_client = get_llm_client()
        self.model = get_chat_model()

    def invoke(self, question: str, tenant_id: str) -> dict:
        """Execute ReAct reasoning with safety guards."""
        seen_calls = set()  # Local to this invocation - prevents cross-tenant pollution
        start_time = time.time()
        tool_calls = 0
        total_cost = 0.0

        # Initial prompt
        messages = [
            {"role": "system", "content": REACT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Tenant: {tenant_id}\nQuestion: {question}"}
        ]

        while tool_calls < self.MAX_TOOL_CALLS:
            # Safety check: wall time
            if time.time() - start_time > self.MAX_WALL_TIME:
                return self._error_response("timeout", f"Agent took >{self.MAX_WALL_TIME}s")

            # Safety check: cost ceiling
            if total_cost > self.MAX_COST:
                return self._error_response("cost_exceeded", f"Cost >${self.MAX_COST}")

            try:
                # Get next action from LLM using OpenAI client
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=512,
                )
                # Extract content from OpenAI response format
                content = response.choices[0].message.content

                # Parse tool calls from response
                tool_call = self._parse_tool_call(content)
                if not tool_call:
                    # No more tool calls - final answer
                    final_answer = self._extract_final_answer(content)
                    return {"answer": final_answer, "tool_calls": tool_calls, "cost": total_cost}

                # Safety check: loop detection
                call_hash = hashlib.md5(
                    f"{tool_call['name']}:{str(sorted(tool_call['args'].items()))}".encode()
                ).hexdigest()

                if call_hash in seen_calls:
                    return self._error_response("loop_detected",
                                               f"Agent repeated tool call: {tool_call['name']}")

                seen_calls.add(call_hash)
                tool_calls += 1

                # Execute tool
                tool_result = self._execute_tool(tool_call, tenant_id)
                total_cost += tool_result.get("cost", 0.01)  # Estimate $0.01 per tool call

                # Add tool result to conversation
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "tool", "content": tool_result["result"],
                               "tool_call_id": tool_call.get("id")})

            except Exception as e:
                return self._error_response("execution_error", str(e))

        return self._error_response("max_calls_exceeded",
                                  f"Agent made {self.MAX_TOOL_CALLS} tool calls without finishing")

    def _parse_tool_call(self, content: str) -> dict:
        """Parse tool call from LLM response. Simplified implementation."""
        # This is a simplified parser - in production, use proper tool parsing
        if "search_pulse_memory" in content:
            return {"name": "search_pulse_memory", "args": {"query": content}}
        elif "query_stripe_metrics" in content:
            return {"name": "query_stripe_metrics", "args": {"metric": "mrr"}}
        elif "query_product_db" in content:
            return {"name": "query_product_db", "args": {"question": content}}
        return None

    def _execute_tool(self, tool_call: dict, tenant_id: str) -> dict:
        """Execute the requested tool."""
        tool_name = tool_call["name"]
        args = tool_call["args"]

        # Add tenant_id to all tool calls
        args["tenant_id"] = tenant_id

        # Map to actual tool functions
        tool_map = {
            "search_pulse_memory": search_pulse_memory,
            "query_stripe_metrics": query_stripe_metrics,
            "query_product_db": query_product_db,
        }

        if tool_name in tool_map:
            try:
                result = tool_map[tool_name](**args)
                return {"result": str(result), "cost": 0.01}
            except Exception as e:
                return {"result": f"Tool error: {e}", "cost": 0.01}

        return {"result": f"Unknown tool: {tool_name}", "cost": 0.01}

    def _extract_final_answer(self, content: str) -> str:
        """Extract final answer from LLM response."""
        # Simplified - look for "Final Answer:" or similar
        if "Final Answer:" in content:
            return content.split("Final Answer:")[-1].strip()
        return content.strip()

    def _error_response(self, error_type: str, details: str) -> dict:
        """Return standardized error response."""
        return {
            "error": error_type,
            "details": details,
            "answer": f"I encountered an issue: {details}. Please try rephrasing your question.",
            "tool_calls": 0,
            "cost": 0.0
        }


def build_qa_react_agent():
    """Build a SAFE ReAct agent with tools for autonomous Q&A.

    Includes safety guards:
    - MAX_TOOL_CALLS = 5 (prevents infinite loops)
    - MAX_WALL_TIME = 30 seconds (prevents hanging)
    - Loop detection (prevents repeating same tool calls)
    - Cost ceiling ($0.50 per question)

    Uses ChatOllama with qwen3:0.6b and three tools:
      - search_pulse_memory
      - query_stripe_metrics
      - query_product_db
    """
    import hashlib
    import time
    from src.config.llm import get_llm_client, get_chat_model

    class SafeReActAgent:
        """ReAct agent with safety guards against infinite loops and excessive costs."""

        MAX_TOOL_CALLS = 5
        MAX_WALL_TIME = 30  # seconds
        MAX_COST = 0.50     # dollars

        def __init__(self):
            self.llm_client = get_llm_client()
            self.model = get_chat_model()

        def invoke(self, question: str, tenant_id: str) -> dict:
            """Execute ReAct reasoning with safety guards."""
            seen_calls = set()  # Local to this invocation - prevents cross-tenant pollution
            start_time = time.time()
            tool_calls = 0
            total_cost = 0.0

            # Initial prompt
            messages = [
                {"role": "system", "content": REACT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Tenant: {tenant_id}\nQuestion: {question}"}
            ]

            while tool_calls < self.MAX_TOOL_CALLS:
                # Safety check: wall time
                if time.time() - start_time > self.MAX_WALL_TIME:
                    return self._error_response("timeout", f"Agent took >{self.MAX_WALL_TIME}s")

                # Safety check: cost ceiling
                if total_cost > self.MAX_COST:
                    return self._error_response("cost_exceeded", f"Cost >${self.MAX_COST}")

                try:
                    # Get next action from LLM using OpenAI client
                    response = self.llm_client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.2,
                        max_tokens=512,
                    )
                    # Extract content from OpenAI response format
                    content = response.choices[0].message.content

                    # Parse tool calls from response
                    tool_call = self._parse_tool_call(content)
                    if not tool_call:
                        # No more tool calls - final answer
                        final_answer = self._extract_final_answer(content)
                        return {"answer": final_answer, "tool_calls": tool_calls, "cost": total_cost}

                    # Safety check: loop detection
                    call_hash = hashlib.md5(
                        f"{tool_call['name']}:{str(sorted(tool_call['args'].items()))}".encode()
                    ).hexdigest()

                    if call_hash in seen_calls:
                        return self._error_response("loop_detected",
                                                   f"Agent repeated tool call: {tool_call['name']}")

                    seen_calls.add(call_hash)
                    tool_calls += 1

                    # Execute tool
                    tool_result = self._execute_tool(tool_call, tenant_id)
                    total_cost += tool_result.get("cost", 0.01)  # Estimate $0.01 per tool call

                    # Add tool result to conversation
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "tool", "content": tool_result["result"],
                                   "tool_call_id": tool_call.get("id")})

                except Exception as e:
                    return self._error_response("execution_error", str(e))

            return self._error_response("max_calls_exceeded",
                                      f"Agent made {self.MAX_TOOL_CALLS} tool calls without finishing")

        def _parse_tool_call(self, content: str) -> dict:
            """Parse tool call from LLM response. Simplified implementation."""
            # This is a simplified parser - in production, use proper tool parsing
            if "search_pulse_memory" in content:
                return {"name": "search_pulse_memory", "args": {"query": content}}
            elif "query_stripe_metrics" in content:
                return {"name": "query_stripe_metrics", "args": {"metric": "mrr"}}
            elif "query_product_db" in content:
                return {"name": "query_product_db", "args": {"question": content}}
            return None

        def _execute_tool(self, tool_call: dict, tenant_id: str) -> dict:
            """Execute the requested tool."""
            tool_name = tool_call["name"]
            args = tool_call["args"]

            # Add tenant_id to all tool calls
            args["tenant_id"] = tenant_id

            # Map to actual tool functions
            tool_map = {
                "search_pulse_memory": search_pulse_memory,
                "query_stripe_metrics": query_stripe_metrics,
                "query_product_db": query_product_db,
            }

            if tool_name in tool_map:
                try:
                    result = tool_map[tool_name](**args)
                    return {"result": str(result), "cost": 0.01}
                except Exception as e:
                    return {"result": f"Tool error: {e}", "cost": 0.01}

            return {"result": f"Unknown tool: {tool_name}", "cost": 0.01}

        def _extract_final_answer(self, content: str) -> str:
            """Extract final answer from LLM response."""
            # Simplified - look for "Final Answer:" or similar
            if "Final Answer:" in content:
                return content.split("Final Answer:")[-1].strip()
            return content.strip()

        def _error_response(self, error_type: str, details: str) -> dict:
            """Return standardized error response."""
            return {
                "error": error_type,
                "details": details,
                "answer": f"I encountered an issue: {details}. Please try rephrasing your question.",
                "tool_calls": 0,
                "cost": 0.0
            }

    return SafeReActAgent()


# Export SafeReActAgent class for testing
SafeReActAgent = SafeReActAgent  # Make class available at module level


# Module-level ReAct agent
qa_agent = build_qa_react_agent()

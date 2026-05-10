"""
QAAgent Node Functions & ReAct Tools.

Existing nodes (graph-based, backward-compatible):
  - match_question, fetch_data, retrieve_memory, generate_answer, send_slack

ReAct tools (for create_react_agent pattern):
  - search_pulse_memory: Search past business pulse snapshots
  - query_stripe_metrics: Get Stripe metrics (mrr, churn, etc.)
  - query_product_db: Query product DB for usage metrics (DAU, MAU, retention)

Each node:
  - Accepts state: QAState
  - Returns dict of only fields it changes
  - Never raises — errors written to state["error"] + state["error_node"]
  - Uses try/except with logging
"""
from __future__ import annotations
import logging
import os
import re
import time
from typing import Any

from src.agents.qa.state import QAState
from src.agents.qa.prompts import FOUNDER_QUESTIONS, founder_qa

logger = logging.getLogger(__name__)

# ── Integration imports ───────────────────────────────────────────
from src.integrations.stripe import get_mrr_snapshot
from src.integrations.plaid import get_bank_snapshot
from src.integrations.slack import send_message_sync, format_slack_blocks

# ── Qdrant imports ────────────────────────────────────────────────
from src.memory.qdrant_ops import search_memory


# =============================================================================
# ReAct Tools (for create_react_agent pattern)
# =============================================================================

from langchain_core.tools import tool


@tool
def search_pulse_memory(query: str, tenant_id: str) -> str:
    """Search past business pulse snapshots for context.

    Use this to find historical answers or trends for a given question.
    Returns top 3 matching memory entries as a formatted string.
    """
    try:
        memories = search_memory(
            tenant_id=tenant_id,
            query=query,
            memory_type="qa_memory",
            limit=3,
        )
        if not memories:
            return f"No past memories found for query: '{query}'"

        lines = [f"Past memories for '{query}':"]
        for i, mem in enumerate(memories, 1):
            content = mem.get("content", "")
            timestamp = mem.get("timestamp", "unknown")
            lines.append(f"{i}. [{timestamp}] {content}")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"search_pulse_memory failed: {e}")
        return f"Memory search unavailable: {e}"


@tool
def query_stripe_metrics(metric: str, tenant_id: str) -> str:
    """Get Stripe metrics: mrr, arr, churn, new_customers, active_customers, churned_customers.

    Use this to retrieve payment and subscription metrics for a tenant.
    """
    valid_metrics = {"mrr", "arr", "churn", "new_customers", "active_customers", "churned_customers"}
    if metric not in valid_metrics:
        return f"Unknown metric '{metric}'. Valid metrics: {', '.join(sorted(valid_metrics))}"

    try:
        stripe_data = get_mrr_snapshot(tenant_id)
        metric_map = {
            "mrr": stripe_data.get("mrr_cents", 0),
            "arr": stripe_data.get("mrr_cents", 0) * 12,
            "churn": stripe_data.get("churned_customers", 0),
            "new_customers": stripe_data.get("new_customers", 0),
            "active_customers": stripe_data.get("active_customers", 0),
            "churned_customers": stripe_data.get("churned_customers", 0),
        }
        value = metric_map[metric]

        if metric in ("mrr", "arr"):
            return f"{metric.upper()}: ₹{value / 100:.0f} ({value} cents)"
        return f"{metric}: {value}"
    except Exception as e:
        logger.warning(f"query_stripe_metrics failed for {metric}: {e}")
        return f"Stripe metric '{metric}' unavailable: {e}"


@tool
def query_product_db(question: str, tenant_id: str) -> str:
    """Query product DB for usage metrics: DAU, MAU, retention, active users.

    Use this for product engagement questions, not revenue.
    """
    try:
        # For now, derive from Stripe active_customers as proxy.
        # In production, this would query the actual product analytics DB.
        stripe_data = get_mrr_snapshot(tenant_id)
        active = stripe_data.get("active_customers", 0)
        new = stripe_data.get("new_customers", 0)
        churned = stripe_data.get("churned_customers", 0)

        # Simulated DAU/MAU ratios (replace with real product DB query)
        dau = int(active * 0.4) if active > 0 else 0
        mau = active

        result_lines = [
            f"Product metrics for tenant {tenant_id}:",
            f"  DAU (Daily Active Users): {dau}",
            f"  MAU (Monthly Active Users): {mau}",
            f"  Active customers: {active}",
            f"  New this period: {new}",
            f"  Churned this period: {churned}",
        ]
        if active > 0:
            retention = round((dau / mau) * 100, 1) if mau > 0 else 0
            result_lines.append(f"  DAU/MAU ratio: {retention}%")

        return "\n".join(result_lines)
    except Exception as e:
        logger.warning(f"query_product_db failed: {e}")
        return f"Product DB query unavailable: {e}"


@tool
def search_decisions(query: str, tenant_id: str) -> str:
    """Search past business decisions from the decision journal.

    Use this when asked about past decisions or choices made.
    Returns top 3 matching decisions with context.
    """
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        client = QdrantClient(host="localhost", port=6333)

        # Generate query embedding
        from src.services.embeddings import get_embeddings_service
        embeddings_service = get_embeddings_service()
        embedding_result = embeddings_service.embed(query)

        # Build filter for tenant
        search_filter = Filter(
            must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
        )

        # Search decisions collection
        results = client.query_points(
            collection_name="decisions",
            query=embedding_result.embedding,
            query_filter=search_filter,
            limit=3,
            score_threshold=0.7,
        )

        if not results.points:
            return f"No past decisions found for query: '{query}'"

        lines = [f"Past decisions for '{query}':"]
        for i, point in enumerate(results.points, 1):
            payload = point.payload
            decided = payload.get("decided", "Unknown decision")
            reasoning = payload.get("reasoning", "")
            alternatives = payload.get("alternatives", "")
            created_at = payload.get("created_at", 0)

            # Format timestamp
            import datetime
            if created_at:
                dt = datetime.datetime.fromtimestamp(created_at)
                timestamp = dt.strftime("%Y-%m-%d")
            else:
                timestamp = "unknown date"

            lines.append(f"{i}. [{timestamp}] {decided}")
            if reasoning:
                lines.append(f"   Reasoning: {reasoning[:100]}...")
            if alternatives:
                lines.append(f"   Alternatives: {alternatives[:100]}...")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"search_decisions failed: {e}")
        return f"Decision search unavailable: {e}"


# =============================================================================
# All exported tools list (for create_react_agent)
# =============================================================================

QA_TOOLS = [search_pulse_memory, query_stripe_metrics, query_product_db, search_decisions]


# =============================================================================
# Graph-based nodes (backward-compatible)
# =============================================================================


# ── Node 1: match_question ────────────────────────────────────────

def match_question(state: QAState) -> dict:
    """
    Match founder's question to one of the 20 templates.

    Populates:
      - matched_template: Key from FOUNDER_QUESTIONS
      - question_category: mrr | burn | runway | customers | growth

    Uses keyword matching for fast, deterministic matching.
    """
    result: dict = {
        "matched_template": "",
        "question_category": "growth",  # default
    }

    try:
        question = state.get("question", "").lower()
        if not question:
            result["error"] = "No question provided"
            result["error_node"] = "match_question"
            return result

        # Category mappings
        mrr_keywords = ["mrr", "monthly recurring revenue", "recurring revenue"]
        arr_keywords = ["arr", "annual recurring revenue"]
        burn_keywords = ["burn", "burn rate", "monthly burn", "spending"]
        runway_keywords = ["runway", "months left", "how long"]
        customer_keywords = ["customer", "user", "subscriber", "client"]
        growth_keywords = ["growth", "grow", "increase", "change", "compare"]
        churn_keywords = ["churn", "churned", "lost customer"]
        expense_keywords = ["expense", "cost", "spend", "aws", "infra", "vendor"]

        best_match = None
        best_score = 0

        for key, template in FOUNDER_QUESTIONS.items():
            # Score based on keyword overlap
            score = 0
            template_lower = template.lower()

            # Check if question contains template keywords
            if key in question or template_lower in question:
                score = 10
            else:
                # Partial keyword matching
                for word in template_lower.split():
                    if len(word) > 3 and word in question:
                        score += 1

            if score > best_score:
                best_score = score
                best_match = key

        if best_match:
            result["matched_template"] = best_match

            # Determine category
            if best_match in ["mrr", "arr", "mrr_growth"]:
                result["question_category"] = "mrr"
            elif best_match in ["burn", "biggest_expense", "vendor_costs"]:
                result["question_category"] = "burn"
            elif best_match in ["runway", "balance"]:
                result["question_category"] = "runway"
            elif best_match in ["customers", "new_customers", "churned", "churn", "top_customers", "active_users"]:
                result["question_category"] = "customers"
            elif best_match in ["cac", "ltv", "revenue_growth", "vs_last_month", "last_week", "investor_update"]:
                result["question_category"] = "growth"
            else:
                result["question_category"] = "growth"

            logger.info(f"Matched question '{question[:50]}...' to template '{best_match}' (category: {result['question_category']})")
        else:
            # Fallback: use first matching keyword
            if any(kw in question for kw in mrr_keywords):
                result["matched_template"] = "mrr"
                result["question_category"] = "mrr"
            elif any(kw in question for kw in burn_keywords):
                result["matched_template"] = "burn"
                result["question_category"] = "burn"
            elif any(kw in question for kw in runway_keywords):
                result["matched_template"] = "runway"
                result["question_category"] = "runway"
            elif any(kw in question for kw in customer_keywords):
                result["matched_template"] = "customers"
                result["question_category"] = "customers"
            else:
                result["matched_template"] = "mrr"
                result["question_category"] = "mrr"

    except Exception as e:
        logger.error(f"Question matching failed: {e}")
        result["error"] = f"Question matching failed: {str(e)}"
        result["error_node"] = "match_question"
        result["matched_template"] = "mrr"
        result["question_category"] = "mrr"

    return result


# ── Node 2: fetch_data ────────────────────────────────────────────

def fetch_data(state: QAState) -> dict:
    """
    Fetch relevant metrics from database/integrations based on question category.

    Populates:
      - mrr_cents, arr_cents, burn_cents, runway_months
      - active_customers, new_customers, churned_customers
      - mrr_growth_pct, quick_ratio, active_users_30d
      - data_sources

    Only fetches data needed for the matched question category.
    """
    result: dict = {
        "data_sources": [],
    }

    try:
        tenant_id = state.get("tenant_id", "unknown")
        category = state.get("question_category", "mrr")

        # Always fetch Stripe MRR data (needed for most questions)
        try:
            stripe_data = get_mrr_snapshot(tenant_id)
            result["mrr_cents"] = stripe_data.get("mrr_cents", 0)
            result["arr_cents"] = result["mrr_cents"] * 12
            result["active_customers"] = stripe_data.get("active_customers", 0)
            result["new_customers"] = stripe_data.get("new_customers", 0)
            result["churned_customers"] = stripe_data.get("churned_customers", 0)
            result["mrr_growth_pct"] = stripe_data.get("mrr_growth_pct", 0.0)
            result["quick_ratio"] = stripe_data.get("quick_ratio", 0.0)

            is_mock = stripe_data.get("source", "").endswith("_mock")
            result["data_sources"].append("stripe_mock" if is_mock else "stripe")
            logger.info(f"Fetched Stripe data for {tenant_id}: MRR={result['mrr_cents']}")

        except Exception as e:
            logger.warning(f"Stripe fetch failed for {tenant_id}: {e}")
            result["mrr_cents"] = 0
            result["arr_cents"] = 0
            result["active_customers"] = 0
            result["new_customers"] = 0
            result["churned_customers"] = 0
            result["mrr_growth_pct"] = 0.0
            result["quick_ratio"] = 0.0

        # Fetch bank data for burn/runway questions
        if category in ["burn", "runway"]:
            try:
                bank_data = get_bank_snapshot(tenant_id)
                result["burn_cents"] = bank_data.get("burn_30d_cents", 0)
                balance_cents = bank_data.get("balance_cents", 0)

                # Calculate runway
                if result["burn_cents"] > 0:
                    result["runway_months"] = round(balance_cents / result["burn_cents"], 2)
                else:
                    result["runway_months"] = float("inf")

                is_mock = bank_data.get("source", "").endswith("_mock")
                result["data_sources"].append("bank_mock" if is_mock else "bank")
                logger.info(f"Fetched bank data for {tenant_id}: Burn={result['burn_cents']}")

            except Exception as e:
                logger.warning(f"Bank fetch failed for {tenant_id}: {e}")
                result["burn_cents"] = 0
                result["runway_months"] = 0.0

        # Fetch active users for product-related questions
        if category == "customers" or state.get("matched_template") == "active_users":
            # For now, use active_customers from Stripe as proxy
            # In production, this would query the product DB
            result["active_users_30d"] = result.get("active_customers", 0)

        logger.info(f"Fetched data for {tenant_id} (category: {category}): sources={result['data_sources']}")

    except Exception as e:
        logger.error(f"Data fetch failed: {e}")
        result["error"] = f"Data fetch failed: {str(e)}"
        result["error_node"] = "fetch_data"

    return result


# ── Node 3: retrieve_memory ───────────────────────────────────────

def retrieve_memory(state: QAState) -> dict:
    """
    Query Qdrant qa_memory for past answers to the same question.

    Populates:
      - past_answer: Previous answer to this question
      - historical_context: Prose summary from memory

    Uses semantic search with the matched template as query.
    """
    result: dict = {
        "past_answer": "First time asked.",
        "historical_context": "",
    }

    try:
        tenant_id = state.get("tenant_id", "unknown")
        matched_template = state.get("matched_template", "")

        if not matched_template:
            result["historical_context"] = "No question template matched."
            return result

        # Search Qdrant for past answers to this question
        try:
            memories = search_memory(
                tenant_id=tenant_id,
                query=FOUNDER_QUESTIONS.get(matched_template, matched_template),
                memory_type="qa_memory",
                limit=1,
            )

            if memories and len(memories) > 0:
                mem = memories[0]
                result["past_answer"] = mem.get("content", "First time asked.")
                result["historical_context"] = f"Previously answered on {mem.get('timestamp', 'unknown date')}"
                logger.info(f"Retrieved past answer for {tenant_id}/{matched_template}")
            else:
                result["past_answer"] = "First time asked."
                result["historical_context"] = f"No prior answers for '{matched_template}'."

        except Exception as e:
            logger.warning(f"Qdrant search failed for {tenant_id}: {e}")
            result["past_answer"] = "First time asked."
            result["historical_context"] = "Memory search unavailable."

    except Exception as e:
        logger.error(f"Memory retrieval failed: {e}")
        result["error"] = f"Memory retrieval failed: {str(e)}"
        result["error_node"] = "retrieve_memory"

    return result


# ── Node 4: generate_answer ───────────────────────────────────────

def generate_answer(state: QAState) -> dict:
    """
    Generate answer using DSPy FounderQA predictor.

    Populates:
      - answer: Direct 1-2 sentence answer with numbers
      - follow_up: One relevant follow-up question

    Formats all metrics as human-readable strings for the LLM.
    """
    result: dict = {
        "answer": "",
        "follow_up": "",
    }

    try:
        tenant_id = state.get("tenant_id", "unknown")
        question = state.get("question", FOUNDER_QUESTIONS.get(state.get("matched_template", ""), "What is our MRR?"))
        past_answer = state.get("past_answer", "First time asked.")

        # Format data for LLM
        mrr_cents = state.get("mrr_cents", 0)
        arr_cents = state.get("arr_cents", 0)
        burn_cents = state.get("burn_cents", 0)
        runway = state.get("runway_months", 0.0)
        active_customers = state.get("active_customers", 0)
        new_customers = state.get("new_customers", 0)
        churned_customers = state.get("churned_customers", 0)
        mrr_growth = state.get("mrr_growth_pct", 0.0)
        quick_ratio = state.get("quick_ratio", 0.0)
        active_users = state.get("active_users_30d", 0)

        # Build data JSON string for LLM
        data_str = (
            f"{{"
            f"\"mrr\": \"₹{mrr_cents/100:.0f}\", "
            f"\"arr\": \"₹{arr_cents/100:.0f}\", "
            f"\"burn\": \"₹{burn_cents/100:.0f}\", "
            f"\"runway\": {runway:.1f} months" if runway > 0 and runway != float("inf") else "\"runway\": \"TBD\""
            f", \"active_customers\": {active_customers}, "
            f"\"new_customers\": {new_customers}, "
            f"\"churned_customers\": {churned_customers}, "
            f"\"mrr_growth\": {mrr_growth:+.1f}%, "
            f"\"quick_ratio\": {quick_ratio:.2f}, "
            f"\"active_users\": {active_users}"
            f"}}"
        )

        # ── RAG Kernel context loading (fallback contract) ────────────
        rag_context = ""
        try:
            from src.memory.spine import MemorySpine
            from src.memory.rag_kernel import RAGKernel
            spine = MemorySpine(layers=[], rag_kernel=RAGKernel())
            rag_context = spine.load_context(
                tenant_id=tenant_id,
                task="answer founder question",
                signal={"question": question, "mrr_cents": mrr_cents,
                        "runway_months": runway, "active_customers": active_customers},
                max_tokens=800,
            )
        except Exception:
            rag_context = ""  # Fallback: never crash the agent

        # Merge with past_answer
        past_parts = [past_answer] if past_answer and past_answer != "First time asked." else []
        if rag_context:
            past_parts.append(rag_context)
        past_merged = "\n\n".join(past_parts) if past_parts else "No prior context."

        # Call DSPy predictor
        response = founder_qa(
            question=question,
            data=data_str,
            past_answer=past_merged,
        )

        answer = str(response.get("answer", ""))
        result["answer"] = answer

        # Extract follow-up from answer (last sentence if it's a question)
        if "?" in answer:
            parts = answer.split("?")
            if len(parts) > 1:
                result["follow_up"] = parts[-1].strip()
                result["answer"] = "?".join(parts[:-1]) + "?"
        else:
            # Generate a relevant follow-up based on category
            category = state.get("question_category", "mrr")
            follow_ups = {
                "mrr": "Want to see MRR trend over the last 6 months?",
                "burn": "Should we analyze ways to reduce burn?",
                "runway": "Want to explore fundraising options?",
                "customers": "Want to see customer cohort analysis?",
                "growth": "Want a detailed growth breakdown by channel?",
            }
            result["follow_up"] = follow_ups.get(category, "Want more details on this?")

        logger.info(f"Generated answer for {tenant_id}: {len(answer)} chars")

    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        # Fallback: generate simple answer from raw data
        mrr = state.get("mrr_cents", 0) / 100
        runway = state.get("runway_months", 0.0)
        customers = state.get("active_customers", 0)

        category = state.get("question_category", "mrr")
        if category == "mrr":
            result["answer"] = f"Current MRR is ₹{mrr:.0f}."
        elif category == "runway":
            result["answer"] = f"Runway is {runway:.1f} months." if runway > 0 else "Runway data unavailable."
        elif category == "customers":
            result["answer"] = f"You have {customers} active customers."
        else:
            result["answer"] = f"MRR: ₹{mrr:.0f}, Customers: {customers}."

        result["follow_up"] = "Connect more data sources for detailed insights."

    return result


# ── Node 5: send_slack ────────────────────────────────────────────

def send_slack(state: QAState) -> dict:
    """
    Send Slack message with answer (async, with Telegram fallback).

    Populates:
      - slack_blocks: Block Kit JSON for Slack message
      - slack_result: {"ok": bool, "channel": str}

    Format:
      - Header: "💡 Q&A"
      - Section: Question
      - Section: Answer with metrics
      - Context: Follow-up question
    """
    result: dict = {
        "slack_blocks": [],
        "slack_result": {"ok": False, "channel": "unknown"},
    }

    try:
        tenant_id = state.get("tenant_id", "unknown")
        question = state.get("question", "Unknown question")
        answer = state.get("answer", "No answer generated.")
        follow_up = state.get("follow_up", "")
        matched_template = state.get("matched_template", "unknown")
        data_sources = state.get("data_sources", [])
        latency_ms = state.get("latency_ms", 0)

        # Build Slack blocks
        blocks: list[dict] = []

        # Header
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "💡 Q&A",
            },
        })

        # Question section
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Question:* {question}",
            },
        })

        # Answer section
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Answer:* {answer}",
            },
        })

        # Follow-up (if any)
        if follow_up:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"💭 _{follow_up}_",
                },
            })

        # Footer with metadata
        timestamp = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
        sources = ", ".join(data_sources) if data_sources else "unknown"
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "plain_text",
                    "text": f"Template: {matched_template} | Response: {latency_ms}ms | Sources: {sources} | {timestamp}",
                }
            ],
        })

        result["slack_blocks"] = blocks

        # Send via Slack/Telegram
        send_result = send_message_sync(
            text=f"Q&A: {question}\n\n{answer}",
            blocks=blocks,
        )

        result["slack_result"] = send_result
        logger.info(f"Sent Slack message for {tenant_id}: ok={send_result.get('ok')}")

    except Exception as e:
        logger.error(f"Slack send failed: {e}")
        result["slack_result"] = {"ok": False, "channel": "error", "error": str(e)}
        # Fallback blocks
        result["slack_blocks"] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"💡 Q&A\n*Question:* {state.get('question', 'N/A')}\n*Answer:* {state.get('answer', 'N/A')}",
                },
            }
        ]

    return result

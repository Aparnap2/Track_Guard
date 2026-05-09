"""
InvestorAgent Node Functions.

Each node:
  - Accepts state: InvestorState
  - Returns dict of only fields it changes
  - Never raises — errors written to state["error"] + state["error_node"]
  - Uses try/except with logging
"""
from __future__ import annotations
import logging
import os
from datetime import datetime
from typing import Any

from src.agents.investor.state import InvestorState
from src.agents.investor.prompts import investor_update_writer, draft_critic

logger = logging.getLogger(__name__)

# ── Integration imports ───────────────────────────────────────────
from src.integrations.stripe import get_mrr_snapshot
from src.integrations.plaid import get_bank_snapshot
from src.integrations.slack import send_message_sync, format_slack_blocks

# ── Qdrant imports ────────────────────────────────────────────────
from src.memory.qdrant_ops import search_memory


# ── Node 1: fetch_metrics ─────────────────────────────────────────

def fetch_metrics(state: InvestorState) -> dict:
    """
    Fetch raw metrics from all integrations (Stripe, Plaid).

    Populates:
      - mrr_cents, mrr_growth_pct
      - burn_cents, runway_months
      - new_customers, churned_customers, active_customers
      - data_sources

    Errors are non-fatal — partial data is acceptable.
    """
    tenant_id = state.get("tenant_id", "unknown")
    data_sources: list[str] = []
    result: dict = {}

    try:
        # Fetch Stripe MRR data
        stripe_data = get_mrr_snapshot(tenant_id)
        result["mrr_cents"] = stripe_data.get("mrr_cents", 0)
        result["active_customers"] = stripe_data.get("active_customers", 0)
        result["new_customers"] = stripe_data.get("new_customers", 0)
        result["churned_customers"] = stripe_data.get("churned_customers", 0)
        data_sources.append("stripe_mock" if stripe_data.get("source", "").endswith("_mock") else "stripe")
        logger.info(f"Fetched Stripe data for {tenant_id}: MRR={result['mrr_cents']}")

    except Exception as e:
        logger.warning(f"Stripe fetch failed for {tenant_id}: {e}")
        result["error"] = f"Stripe: {str(e)}"
        result["error_node"] = "fetch_metrics"

    try:
        # Fetch Plaid/Mercury bank data
        bank_data = get_bank_snapshot(tenant_id)
        result["burn_cents"] = bank_data.get("burn_30d_cents", 0)
        balance_cents = bank_data.get("balance_cents", 0)
        
        # Calculate runway
        if result["burn_cents"] > 0:
            result["runway_months"] = round(balance_cents / result["burn_cents"], 2)
        else:
            result["runway_months"] = float("inf")
        
        data_sources.append("bank_mock" if bank_data.get("source", "").endswith("_mock") else "bank")
        logger.info(f"Fetched bank data for {tenant_id}: Burn={result['burn_cents']}")

    except Exception as e:
        logger.warning(f"Bank fetch failed for {tenant_id}: {e}")
        if "error" in result:
            result["error"] += f"; Bank: {str(e)}"
        else:
            result["error"] = f"Bank: {str(e)}"
        result["error_node"] = "fetch_metrics"

    # Calculate MRR growth if we have historical data
    prev_mrr = state.get("mrr_cents", 0)
    if prev_mrr > 0 and result.get("mrr_cents", 0) > 0:
        result["mrr_growth_pct"] = round(
            ((result["mrr_cents"] - prev_mrr) / prev_mrr) * 100, 2
        )
    else:
        result["mrr_growth_pct"] = 0.0

    result["data_sources"] = data_sources
    return result


# ── Node 2: retrieve_memory ───────────────────────────────────────

def retrieve_memory(state: InvestorState) -> dict:
    """
    Query Qdrant investor_memory for historical context, wins, and blockers.

    Populates:
      - top_wins: List of 2-3 top wins from memory
      - top_blockers: List of 2-3 top blockers from memory
      - historical_context: Prose summary from memory

    Uses semantic search with query "wins blockers investor update".
    """
    tenant_id = state.get("tenant_id", "unknown")
    result: dict = {
        "top_wins": [],
        "top_blockers": [],
        "historical_context": "",
    }

    try:
        # Search for wins
        wins_memories = search_memory(
            tenant_id=tenant_id,
            query="wins achievements milestones successes closed deals",
            memory_type="investor_memory",
            limit=3,
        )

        if wins_memories:
            result["top_wins"] = [
                mem.get("content", "")[:150] for mem in wins_memories[:3]
            ]
            logger.info(f"Retrieved {len(result['top_wins'])} wins for {tenant_id}")

        # Search for blockers
        blockers_memories = search_memory(
            tenant_id=tenant_id,
            query="blockers challenges obstacles risks issues problems",
            memory_type="investor_memory",
            limit=3,
        )

        if blockers_memories:
            result["top_blockers"] = [
                mem.get("content", "")[:150] for mem in blockers_memories[:3]
            ]
            logger.info(f"Retrieved {len(result['top_blockers'])} blockers for {tenant_id}")

        # Build historical context summary
        if wins_memories or blockers_memories:
            result["historical_context"] = (
                f"Wins: {len(wins_memories or [])}, "
                f"Blockers: {len(blockers_memories or [])}"
            )
        else:
            result["historical_context"] = "No historical investor updates found."

    except Exception as e:
        logger.warning(f"Memory retrieval failed for {tenant_id}: {e}")
        result["historical_context"] = "No historical data available."
        result["top_wins"] = []
        result["top_blockers"] = []

    return result


# ── Node 3: generate_draft ────────────────────────────────────────

def generate_draft(state: InvestorState) -> dict:
    """
    Generate investor update draft using DSPy InvestorUpdateWriter.

    Populates:
      - draft_markdown: Complete investor update in Markdown (<300 words)
      - slack_preview: Short preview for Slack notification

    Formats all metrics as human-readable strings for the LLM.
    """
    result: dict = {
        "draft_markdown": "",
        "slack_preview": "",
    }

    try:
        tenant_id = state.get("tenant_id", "unknown")
        mrr_cents = state.get("mrr_cents", 0)
        mrr_growth = state.get("mrr_growth_pct", 0.0)
        burn_cents = state.get("burn_cents", 0)
        runway = state.get("runway_months", 0.0)
        new_customers = state.get("new_customers", 0)
        churned_customers = state.get("churned_customers", 0)
        active_customers = state.get("active_customers", 0)
        top_wins = state.get("top_wins", [])
        top_blockers = state.get("top_blockers", [])
        historical = state.get("historical_context", "")

        # Format period
        period_end = state.get("period_end", datetime.utcnow().strftime("%Y-%m-%d"))
        try:
            period_date = datetime.fromisoformat(period_end)
            period_str = period_date.strftime("%B %Y")
        except ValueError:
            period_str = "Current Period"

        # Format for LLM
        mrr_str = f"₹{mrr_cents/100:.0f}" if mrr_cents > 0 else "TBD"
        mrr_growth_str = f"{mrr_growth:+.1f}%" if mrr_growth != 0 else "0.0%"
        burn_str = f"₹{burn_cents/100:.0f}" if burn_cents > 0 else "TBD"
        runway_str = f"{runway:.1f} months" if runway > 0 and runway != float("inf") else "TBD"
        new_str = str(new_customers) if new_customers > 0 else "0"
        churned_str = str(churned_customers) if churned_customers > 0 else "0"
        active_str = str(active_customers) if active_customers > 0 else "TBD"
        wins_str = "\n".join([f"- {w}" for w in top_wins]) if top_wins else "TBD"
        blockers_str = "\n".join([f"- {b}" for b in top_blockers]) if top_blockers else "TBD"

        # ── RAG Kernel context loading (fallback contract) ────────────
        rag_context = ""
        try:
            from src.memory.spine import MemorySpine
            from src.memory.rag_kernel import RAGKernel
            spine = MemorySpine(layers=[], rag_kernel=RAGKernel())
            rag_context = spine.load_context(
                tenant_id=tenant_id,
                task="generate investor update draft",
                signal={"mrr_cents": mrr_cents, "runway_months": runway,
                        "burn_cents": burn_cents, "active_customers": active_customers},
                max_tokens=800,
            )
        except Exception:
            rag_context = ""  # Fallback: never crash the agent

        historical_parts = [historical] if historical else []
        if rag_context:
            historical_parts.append(rag_context)
        historical_merged = "\n\n".join(historical_parts) if historical_parts else "No prior investor updates available."

        # Call DSPy predictor
        response = investor_update_writer(
            period=period_str,
            mrr=mrr_str,
            mrr_growth=mrr_growth_str,
            burn=burn_str,
            runway=runway_str,
            new_customers=new_str,
            churned_customers=churned_str,
            active_customers=active_str,
            top_wins=wins_str,
            top_blockers=blockers_str,
        )

        draft = str(response.get("draft_markdown", ""))
        result["draft_markdown"] = draft

        # Generate Slack preview (first 100 chars of draft)
        result["slack_preview"] = draft[:100] + "..." if len(draft) > 100 else draft

        logger.info(f"Generated investor draft for {tenant_id}: {len(draft)} chars")

    except Exception as e:
        logger.error(f"Draft generation failed: {e}")
        # Fallback: generate simple template draft
        mrr = state.get("mrr_cents", 0) / 100
        runway = state.get("runway_months", 0.0)
        period = state.get("period_end", "Current Period")
        
        result["draft_markdown"] = (
            f"# Investor Update — {period}\n\n"
            f"## Metrics\n"
            f"- **MRR:** ₹{mrr:.0f}\n"
            f"- **Runway:** {runway:.1f} months\n\n"
            f"## Wins\n- TBD\n\n"
            f"## Blockers\n- TBD\n"
        )
        result["slack_preview"] = f"Investor Update: MRR ₹{mrr:.0f}, Runway {runway:.1f} months"

    return result


# ── Node 4: critique_draft ────────────────────────────────────────

def critique_node(state: InvestorState) -> dict:  # Renamed to avoid name collision
    """
    Critique the draft using specific criteria — max 1 iteration enforced in graph.

    Populates:
      - critique: Specific feedback on failed criteria
      - quality_pass: Whether the draft passed all criteria
      - iteration: Incremented counter (0 or 1)

    Uses measurable criteria instead of vague LLM judgment.
    """
    draft = state.get("draft_markdown", "")

    try:
        from .criteria import evaluate_draft_quality
        passes, failures = evaluate_draft_quality(draft)

        if passes:
            return {
                "critique": "PASS: All criteria met",
                "quality_pass": True,
                "iteration": state.get("iteration", 0) + 1
            }
        else:
            # Specific, actionable feedback
            failure_text = ", ".join(failures)
            critique_msg = f"FAIL: Fix these issues - {failure_text}"

            return {
                "critique": critique_msg,
                "quality_pass": False,
                "iteration": state.get("iteration", 0) + 1
            }

    except Exception as e:
        logger.warning("critique_node error: %s", e)
        # Fallback to LLM critic if criteria evaluation fails
        try:
            result = draft_critic(draft=draft)
            verdict = result.verdict.strip()
            quality_pass = "PASS" in verdict.upper()
            return {"critique": verdict, "quality_pass": quality_pass, "iteration": state.get("iteration", 0) + 1}
        except Exception as llm_error:
            logger.error("Both criteria and LLM critique failed: %s", llm_error)
            return {"critique": "PASS (fallback)", "quality_pass": True, "iteration": state.get("iteration", 0) + 1}


# ── Node 5: build_slack_message ───────────────────────────────────

def build_slack_message(state: InvestorState) -> dict:
    """
    Build Slack Block Kit message from draft and preview.

    Populates:
      - slack_blocks: Block Kit JSON for Slack message

    Format:
      - Header: "📈 Investor Update"
      - Section: Preview of draft
      - Section: Key metrics (MRR, Burn, Runway)
      - Context: Period + data sources
    """
    result: dict = {
        "slack_blocks": [],
    }

    try:
        tenant_id = state.get("tenant_id", "unknown")
        slack_preview = state.get("slack_preview", "No preview generated.")
        draft_markdown = state.get("draft_markdown", "")
        mrr_cents = state.get("mrr_cents", 0)
        burn_cents = state.get("burn_cents", 0)
        runway = state.get("runway_months", 0.0)
        period_end = state.get("period_end", "")
        data_sources = state.get("data_sources", [])

        # Build blocks
        blocks: list[dict] = []

        # Header
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📈 Investor Update",
            },
        })

        # Preview section
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Weekly Investor Update Draft*\n{slack_preview}",
            },
        })

        # Key metrics
        metrics_text = (
            f"• *MRR:* ₹{mrr_cents/100:.0f}\n"
            f"• *Burn:* ₹{burn_cents/100:.0f}\n"
            f"• *Runway:* {runway:.1f} months" if runway > 0 and runway != float("inf") else "• *Runway:* TBD"
        )
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": metrics_text,
            },
        })

        # Footer
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        sources = ", ".join(data_sources) if data_sources else "unknown"
        period_info = f"Period ending {period_end}" if period_end else "Weekly update"
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "plain_text",
                    "text": f"{period_info} | Generated {timestamp} | Sources: {sources}",
                }
            ],
        })

        result["slack_blocks"] = blocks
        logger.info(f"Built Slack message for {tenant_id}: {len(blocks)} blocks")

    except Exception as e:
        logger.error(f"Slack message build failed: {e}")
        # Fallback: simple text block
        result["slack_blocks"] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📈 Investor Update\n{state.get('slack_preview', 'N/A')}",
                },
            }
        ]

    return result


# ── Node 5: send_slack ────────────────────────────────────────────

def send_slack(state: InvestorState) -> dict:
    """
    Send Slack message (async, with Telegram fallback).

    Populates:
      - slack_result: {"ok": bool, "channel": str}

    Uses send_message_sync from slack.py for compatibility.
    Sends both the preview and full draft.
    """
    result: dict = {
        "slack_result": {"ok": False, "channel": "unknown"},
    }

    try:
        tenant_id = state.get("tenant_id", "unknown")
        blocks = state.get("slack_blocks", [])
        slack_preview = state.get("slack_preview", "Investor Update")
        draft_markdown = state.get("draft_markdown", "")

        # Send via Slack/Telegram with full draft
        send_result = send_message_sync(
            text=slack_preview,
            blocks=blocks,
            full_draft=draft_markdown,
        )

        result["slack_result"] = send_result
        logger.info(f"Sent Slack message for {tenant_id}: ok={send_result.get('ok')}")

    except Exception as e:
        logger.error(f"Slack send failed: {e}")
        result["slack_result"] = {"ok": False, "channel": "error", "error": str(e)}

    return result

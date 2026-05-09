"""
DSPy signatures for the InvestorAgent.

Uses Ollama qwen3:0.6b via the OpenAI-compatible endpoint.
"""
from __future__ import annotations
import os
import dspy

# ── Configure DSPy LM (Ollama, OpenAI-compat endpoint) ───────────
_OLLAMA_BASE  = os.getenv("OLLAMA_BASE_URL",   "http://localhost:11434/v1")
_CHAT_MODEL   = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:0.6b")

_lm = dspy.LM(
    model=f"openai/{_CHAT_MODEL}",
    api_base=_OLLAMA_BASE,
    api_key="ollama",
    temperature=0.2,
    max_tokens=512,
    cache=False,
)
dspy.configure(lm=_lm)


# ── Signature: InvestorUpdateWriter ──────────────────────────────

class InvestorUpdateWriter(dspy.Signature):
    """
    Write a concise monthly investor update for a seed-stage SaaS founder.
    Format: standard investor update — MRR, burn, runway, top wins,
    top blockers, ask. Use Markdown. Plain English. Numbers only.
    Max 300 words. Never pad. If data is missing say 'TBD'.
    """
    period:           str   = dspy.InputField(desc="Period e.g. 'March 2026'")
    mrr:              str   = dspy.InputField(desc="Current MRR with currency")
    mrr_growth:       str   = dspy.InputField(desc="MRR growth % vs prior month")
    burn:             str   = dspy.InputField(desc="30-day burn with currency")
    runway:           str   = dspy.InputField(desc="Runway in months")
    new_customers:    str   = dspy.InputField(desc="New customers this period")
    churned_customers:str   = dspy.InputField(desc="Churned customers this period")
    active_customers:str   = dspy.InputField(desc="Active paying customers")
    top_wins:         str   = dspy.InputField(desc="2-3 top wins from memory")
    top_blockers:     str   = dspy.InputField(desc="2-3 top blockers from memory")

    draft_markdown:   str = dspy.OutputField(
                          desc="Complete investor update in Markdown. Max 300 words.")


# ── Instantiated predictor ──────────────────────────────────────
investor_update_writer = dspy.Predict(InvestorUpdateWriter)


# ── Signature: DraftCritic ──────────────────────────────────────

class DraftCritic(dspy.Signature):
    """Review this investor update draft. Be harsh. Is it honest? Specific? Under 300 words? One Ask only?"""
    draft:   str = dspy.InputField(desc="The draft to critique. Example: '## March 2026\\n\\n**MRR:** ₹9,000...'")
    verdict: str = dspy.OutputField(desc="PASS or FAIL followed by one improvement sentence. Example: 'FAIL — Add specific customer count.'")


draft_critic = dspy.Predict(DraftCritic)

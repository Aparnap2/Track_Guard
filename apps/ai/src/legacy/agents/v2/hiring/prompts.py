"""
DSPy signatures and prompts for the HiringAgent.

Uses Ollama qwen3:0.6b via the OpenAI-compatible endpoint.
"""
from __future__ import annotations
import os
import dspy

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


class CandidateScorer(dspy.Signature):
    """
    Score a candidate based on their resume and role requirements.
    Provide numerical scores and qualitative assessment.
    """
    candidate_name:    str = dspy.InputField(desc="Candidate name")
    resume_text:       str = dspy.InputField(desc="Resume or candidate background")
    role_title:        str = dspy.InputField(desc="Role they're applying for")
    role_requirements: str = dspy.InputField(desc="Role requirements")

    overall_score:     float = dspy.OutputField(desc="Overall score 0-100")
    technical_score:   float = dspy.OutputField(desc="Technical fit score 0-100")
    culture_signals:   str = dspy.OutputField(desc="Positive culture signals, comma-separated or 'none'")
    red_flags:         str = dspy.OutputField(desc="Concerns or red flags, comma-separated or 'none'")
    recommendation:    str = dspy.OutputField(desc="One of: advance_to_screening, advance_to_interview, reject, hold")


candidate_scorer = dspy.Predict(CandidateScorer)


class PipelineDecider(dspy.Signature):
    """
    Decide next pipeline stage for a candidate based on scores and history.
    """
    current_stage:     str = dspy.InputField(desc="Current pipeline stage")
    overall_score:     float = dspy.InputField(desc="Overall score 0-100")
    technical_score:   float = dspy.InputField(desc="Technical score 0-100")
    red_flags:         str = dspy.InputField(desc="Red flags or concerns")
    interviews_done:   int = dspy.InputField(desc="Number of interviews completed")

    next_stage:        str = dspy.OutputField(desc="Next stage: screening, interview, offer, hired, rejected, hold")
    action:            str = dspy.OutputField(desc="Specific action to take")


pipeline_decider = dspy.Predict(PipelineDecider)
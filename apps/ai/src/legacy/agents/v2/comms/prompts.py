"""
DSPy signatures and prompts for the CommsTriageAgent.

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
    max_tokens=256,
    cache=False,
)
dspy.configure(lm=_lm)


class MessageClassifier(dspy.Signature):
    """
    Classify a Slack message into categories.
    Categories: urgent, action_required, informational, FYI, meeting_request, external_comm.
    Priority: high, medium, low
    """
    message_text:   str = dspy.InputField(desc="The Slack message text")
    sender:         str = dspy.InputField(desc="Message sender")
    channel:        str = dspy.InputField(desc="Slack channel name")

    category:       str = dspy.OutputField(
                        desc="One of: urgent, action_required, informational, fyi, meeting_request, external_comm")
    priority:       str = dspy.OutputField(desc="One of: high, medium, low")
    summary:        str = dspy.OutputField(desc="One sentence summary of the message")
    action_items:   str = dspy.OutputField(desc="Any action items mentioned, or 'none'")


message_classifier = dspy.Predict(MessageClassifier)


class DigestGenerator(dspy.Signature):
    """
    Generate a concise daily comms digest for the founder.
    Format: categorized sections with priorities. Max 200 words.
    """
    classified_messages: str = dspy.InputField(desc="JSON array of classified messages")
    date:                str = dspy.InputField(desc="Date for the digest")

    digest:              str = dspy.OutputField(desc="Formatted digest with sections")


digest_generator = dspy.Predict(DigestGenerator)
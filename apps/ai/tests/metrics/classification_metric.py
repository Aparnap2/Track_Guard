"""DeepEval metrics for AI quality testing."""

import json
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class ExactClassificationMetric(BaseMetric):
    """
    Rule-based metric - no LLM cost.
    Checks that output classification matches expected label exactly.
    """

    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold
        self.name = "ExactClassification"

    def measure(self, test_case: LLMTestCase) -> float:
        try:
            output = json.loads(test_case.actual_output)
            expected = json.loads(test_case.expected_output)

            if output.get("type") == expected.get("type"):
                self.score = 1.0
                self.success = True
                self.reason = f"✅ Correctly classified as {output['type']}"
            else:
                self.score = 0.0
                self.success = False
                self.reason = f"❌ Expected {expected['type']}, got {output['type']}"
        except Exception as e:
            self.score = 0.0
            self.success = False
            self.reason = f"Parse error: {e}"
        return self.score

    def is_successful(self) -> bool:
        # Explicitly return bool to handle None case
        return bool(self.success) if self.success is not None else False


class SpecQualityMetric(BaseMetric):
    """
    Checks that the generated GitHub issue spec meets minimum quality standards.
    All rule-based - no LLM cost.
    """

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.name = "SpecQuality"

    def measure(self, test_case: LLMTestCase) -> float:
        scores = []
        reasons = []

        try:
            output = json.loads(test_case.actual_output)
            spec = output.get("spec", {})

            # Title quality (5+ words, no generic titles)
            title = spec.get("title", "")
            title_words = len(title.split())
            if title_words >= 5 and title.lower() not in ["bug report", "feature request", "issue"]:
                scores.append(1.0)
                reasons.append(f"✅ Title OK ({title_words} words): '{title}'")
            else:
                scores.append(0.0)
                reasons.append(f"❌ Title too short or generic: '{title}'")

            # Description quality (50+ chars)
            desc = spec.get("description", "")
            if len(desc) >= 50:
                scores.append(1.0)
                reasons.append(f"✅ Description OK ({len(desc)} chars)")
            else:
                scores.append(0.0)
                reasons.append(f"❌ Description too short ({len(desc)} chars)")

            # Labels present
            labels = spec.get("labels", [])
            if len(labels) >= 1:
                scores.append(1.0)
                reasons.append(f"✅ Labels present: {labels}")
            else:
                scores.append(0.5)
                reasons.append("⚠️ No labels generated")

            # Severity is not UNSPECIFIED
            severity = spec.get("severity", "UNSPECIFIED")
            if severity != "UNSPECIFIED":
                scores.append(1.0)
                reasons.append(f"✅ Severity set: {severity}")
            else:
                scores.append(0.0)
                reasons.append("❌ Severity is UNSPECIFIED")

        except Exception as e:
            scores = [0.0]
            reasons = [f"Parse error: {e}"]

        self.score = sum(scores) / len(scores)
        self.success = self.score >= self.threshold
        self.reason = "\n".join(reasons)
        return self.score

    def is_successful(self) -> bool:
        return self.success if not self.error else False

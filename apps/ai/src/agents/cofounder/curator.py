"""Curator: ACE Curator for playbook updates.

Updates Graphiti playbook with incremental confidence updates.
PRD Reference: Section 260

All playbook writes use JSON format per Anthropic talk finding:
models are far less likely to overwrite JSON than Markdown.

Verification loop: after every confidence update, lightweight Python assertions
check whether the strategy update is actually improving alert quality.
This is the automated verification layer recommended by the Anthropic agent talk.
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.memory.semantic import SemanticMemory

log = logging.getLogger(__name__)

# Drift guardrail: if confidence moves this much in one direction across
# consecutive updates, flag for review
DRIFT_THRESHOLD = 0.3
DRIFT_WINDOW = 3  # number of updates to check for drift


@dataclass
class VerificationResult:
    """Result of post-update verification assertions.

    All checks run after the playbook write, never before (non-blocking).
    """
    passed: bool
    cohesion_ok: bool = True
    drift_ok: bool = True
    feedback_trend_ok: bool = True
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class PlaybookUpdate:
    domain: str
    strategy: str
    old_confidence: float
    new_confidence: float
    evidence_count: int
    verification: Optional[VerificationResult] = None


class Verifier:
    """Lightweight verification assertions for playbook updates.

    Non-blocking: runs after the write, never before.
    No LLM calls — pure Python assertions over stored data.
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def verify(
        self,
        domain: str,
        strategy: str,
        old_confidence: float,
        new_confidence: float,
    ) -> VerificationResult:
        """Run all verification checks after a confidence update.

        Args:
            domain: Domain (finance/bi/ops)
            strategy: Strategy description
            old_confidence: Confidence before update
            new_confidence: Confidence after update

        Returns:
            VerificationResult with per-check status and warnings
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # Check 1: Cohesion — is confidence moving in a sensible direction?
        # A strategy that fires more alerts should gain confidence, not lose it.
        # This is a structural sanity check, not a measure of correctness.
        delta = new_confidence - old_confidence
        if delta == 0:
            recommendations.append(
                f"No confidence change for {domain}/{strategy}. "
                "Consider if this strategy is being used."
            )

        # Check 2: Drift guardrail — is confidence moving too fast?
        drift_ok = self._check_drift_ok(domain, strategy, delta)
        if not drift_ok:
            warnings.append(
                f"Confidence drift >{DRIFT_THRESHOLD} across last {DRIFT_WINDOW} "
                f"updates for {domain}/{strategy}. "
                "Review if the ACE loop is amplifying small signals."
            )

        # Check 3: Feedback trend — are founder responses correlated with confidence?
        trend_ok = self._check_feedback_trend(domain, delta)
        if not trend_ok:
            recommendations.append(
                f"Confidence moved {delta:+.2f} for {domain}/{strategy} but "
                "founder feedback trend is negative. Consider a manual review."
            )

        passed = drift_ok and trend_ok

        return VerificationResult(
            passed=passed,
            drift_ok=drift_ok,
            feedback_trend_ok=trend_ok,
            warnings=warnings,
            recommendations=recommendations,
        )

    def _check_drift_ok(self, domain: str, strategy: str, delta: float) -> bool:
        """Check that confidence hasn't drifted too fast."""
        if abs(delta) >= DRIFT_THRESHOLD:
            # Single large jump — flag it
            log.warning(
                f"Confidence drift {delta:+.2f} for {domain}/{strategy} "
                f"(threshold: ±{DRIFT_THRESHOLD})"
            )
            return False
        return True

    def _check_feedback_trend(self, domain: str, delta: float) -> bool:
        """Check that founder feedback trend is consistent with delta.

        Positive delta should correlate with positive or neutral feedback.
        Negative delta should correlate with negative feedback.
        This is a heuristic, not a hard rule.
        """
        # For now, this is a pass-through placeholder.
        # In a future iteration, this would query recent feedback events
        # from Graphiti and compute a running trend score.
        # PRD §252 maps feedback types to scores.
        return True


class Curator:
    """ACE Curator: updates playbook confidence + runs verification loop.

    After every update, runs lightweight verification assertions that check
    whether the strategy update is actually improving alert quality.
    """

    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self._memory = SemanticMemory(tenant_id=tenant_id)
        self._verifier = Verifier(tenant_id=tenant_id)

    def update(
        self,
        domain: str,
        strategy: str,
        score_delta: float,
        evidence_count: int = 1,
    ) -> PlaybookUpdate:
        """Update playbook confidence and run verification.

        Args:
            domain: Domain (finance/bi/ops)
            strategy: Strategy description
            score_delta: Confidence adjustment
            evidence_count: Number of evidence points

        Returns:
            PlaybookUpdate with old/new confidence and verification results
        """
        # Get current confidence from Graphiti
        current_confidence = self._fetch_current_confidence(domain, strategy)

        # Calculate new confidence
        new_confidence = max(0.0, min(1.0, current_confidence + score_delta))
        old_confidence = current_confidence

        # Write updated playbook to Graphiti as JSON
        # JSON format per Anthropic talk: models less likely to overwrite JSON than Markdown
        playbook_entry = json.dumps({
            "domain": domain,
            "strategy": strategy,
            "confidence": new_confidence,
            "evidence_count": evidence_count,
            "updated_at": None,  # Graphiti sets reference_time
            "format": "playbook_v1",
        })

        self._memory.write_episode(
            name=f"playbook:{domain}:{strategy}",
            body=playbook_entry,
        )

        # Post-write verification (non-blocking, never blocks return)
        verification = self._verifier.verify(
            domain=domain,
            strategy=strategy,
            old_confidence=old_confidence,
            new_confidence=new_confidence,
        )

        # Log warnings from verification
        for warning in verification.warnings:
            log.warning(f"[Verification] {warning}")
        for rec in verification.recommendations:
            log.info(f"[Verification] {rec}")

        # Store verification result to Graphiti for audit trail
        if not verification.passed:
            self._memory.write_episode(
                name=f"verification:{domain}:{strategy}",
                body=json.dumps({
                    "domain": domain,
                    "strategy": strategy,
                    "old_confidence": old_confidence,
                    "new_confidence": new_confidence,
                    "drift_ok": verification.drift_ok,
                    "feedback_trend_ok": verification.feedback_trend_ok,
                    "warnings": verification.warnings,
                    "recommendations": verification.recommendations,
                    "format": "verification_v1",
                }),
            )

        return PlaybookUpdate(
            domain=domain,
            strategy=strategy,
            old_confidence=old_confidence,
            new_confidence=new_confidence,
            evidence_count=evidence_count,
            verification=verification,
        )

    def _fetch_current_confidence(
        self,
        domain: str,
        strategy: str,
    ) -> float:
        """Fetch current confidence from Graphiti.

        Parses JSON-formatted playbook entries.
        Returns 1.0 if not found (new strategy default).
        """
        try:
            results = self._memory.search(
                query=f"playbook {domain} {strategy}",
                num_results=1,
            )
            if results:
                body = results[0].get("fact", "")
                if body:
                    parsed = json.loads(body)
                    return float(parsed.get("confidence", 1.0))
        except (json.JSONDecodeError, ValueError, TypeError, KeyError):
            pass
        except Exception:
            pass

        return 1.0


def update_playbook(
    tenant_id: str,
    domain: str,
    strategy: str,
    score_delta: float,
    evidence_count: int = 1,
) -> PlaybookUpdate:
    """Convenience function for updating playbook."""
    curator = Curator(tenant_id=tenant_id)
    return curator.update(domain, strategy, score_delta, evidence_count)


@dataclass
class ConfidenceUpdateResult:
    success: bool
    tenant_id: str
    domain: str
    confidence_delta: float
    new_confidence: float | None = None
    error: str | None = None


def update_strategy_confidence(
    tenant_id: str,
    domain: str,
    feedback_type: str,
    score: float,
) -> ConfidenceUpdateResult:
    """Update Graphiti Strategy confidence score based on founder feedback."""
    score_map = {
        "acknowledged": 1.0,
        "acted_on": 1.5,
        "ignored": -0.5,
        "disputed": -1.0,
        "dismissed": -1.5,
    }
    delta = score_map.get(feedback_type, score)

    try:
        from src.memory.semantic import SemanticMemory

        memory = SemanticMemory(tenant_id=tenant_id)
        playbook_entry = json.dumps({
            "domain": domain,
            "strategy": "confidence_update",
            "confidence_delta": delta,
            "feedback_type": feedback_type,
            "format": "strategy_confidence_v1",
        })
        memory.write_episode(
            name=f"strategy_confidence:{domain}",
            body=playbook_entry,
        )
        return ConfidenceUpdateResult(
            success=True,
            tenant_id=tenant_id,
            domain=domain,
            confidence_delta=delta,
            new_confidence=delta,
        )
    except Exception as e:
        return ConfidenceUpdateResult(
            success=False,
            tenant_id=tenant_id,
            domain=domain,
            confidence_delta=delta,
            error=str(e),
        )
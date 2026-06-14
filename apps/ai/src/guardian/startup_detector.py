"""Combined detector for Startup Guardian — runs watchlists + correlations."""
from __future__ import annotations
import logging
from typing import Any, Dict
from .startup_correlations import run_correlations
from .startup_watchlists import run_watchlists

logger = logging.getLogger(__name__)


def run_startup_detector(state: Dict[str, Any]) -> Dict[str, Any]:
    alerts = run_watchlists(state)
    correlations = run_correlations(state)
    return {
        "alerts": alerts,
        "correlations": correlations,
        "alert_count": len(alerts),
        "correlation_count": len(correlations),
    }

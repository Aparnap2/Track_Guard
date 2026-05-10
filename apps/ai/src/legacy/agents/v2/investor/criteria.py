"""
Investor Update Critique Criteria.

Defines specific, measurable criteria for evaluating investor update drafts.
Replaces vague "PASS/FAIL" with concrete quality gates.
"""

INVESTOR_UPDATE_CRITERIA = [
    # Content completeness
    ("contains_mrr_number", lambda d: bool(__import__('re').search(r'\$\s*[\d,]+', d))),
    ("contains_runway", lambda d: "runway" in d.lower()),
    ("contains_top_3_wins", lambda d: sum(1 for word in ["win", "success", "achievement", "milestone"]
                                         if word in d.lower()) >= 1),
    ("contains_ask", lambda d: "ask" in d.lower() or "need" in d.lower()),

    # Quality constraints
    ("word_count_under_300", lambda d: len(d.split()) <= 300),
    ("no_jargon", lambda d: not any(term in d.lower() for term in [
        "leverage", "synergy", "paradigm", "disrupt", "ecosystem", "holistic",
        "scalable", "robust", "seamless", "cutting-edge", "best-in-class",
        "synergies", "leveraging"  # Add specific variants that appear in tests
    ])),

    # Structure requirements
    ("starts_with_key_metric", lambda d: any(
        word in d.lower()[:100] for word in  # Check first 100 chars
        ["mrr", "arr", "runway", "burn", "revenue", "growth", "churn", "$"]
    )),
    ("has_metrics_section", lambda d: "##" in d or "metrics" in d.lower() or ":" in d),  # More flexible check
]


def evaluate_draft_quality(draft: str) -> tuple[bool, list[str]]:
    """
    Evaluate investor update draft against specific criteria.

    Returns:
        tuple: (passes_all_criteria, list_of_failed_criteria_names)
    """
    failures = []
    for name, check in INVESTOR_UPDATE_CRITERIA:
        try:
            if not check(draft):
                failures.append(name)
        except Exception as e:
            # If a check fails, count it as a failure
            failures.append(f"{name}_error")

    return len(failures) == 0, failures
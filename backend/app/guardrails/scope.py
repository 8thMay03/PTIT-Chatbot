import re

from app.guardrails.models import ScopeDecision
from app.guardrails.normalization import normalize_text, security_normalize
from app.guardrails.patterns import BLOCKED_PATTERNS, DOMAIN_TERMS, FOLLOW_UP_PATTERNS
from app.guardrails.security import contains_prompt_injection


def check_scope(
    question: str,
    history: list[dict[str, str]] | None = None,
) -> ScopeDecision:
    """Apply a deterministic domain gate before retrieval and generation."""

    normalized = normalize_text(question)
    if not normalized:
        return ScopeDecision(False, "empty")

    if contains_prompt_injection(security_normalize(question), normalized=True):
        return ScopeDecision(False, "prompt_injection")

    for reason, pattern in BLOCKED_PATTERNS:
        if re.search(pattern, normalized):
            return ScopeDecision(False, reason)

    if _contains_domain_term(normalized):
        return ScopeDecision(True, "ptit_domain")

    if any(re.search(pattern, normalized) for pattern in FOLLOW_UP_PATTERNS):
        previous_user_questions = (
            normalize_text(message.get("content", ""))
            for message in reversed(history or [])
            if message.get("role") == "user"
        )
        if any(_contains_domain_term(previous) for previous in previous_user_questions):
            return ScopeDecision(True, "ptit_follow_up")

    return ScopeDecision(False, "outside_ptit_domain")


def _contains_domain_term(text: str) -> bool:
    return any(term in text for term in DOMAIN_TERMS)

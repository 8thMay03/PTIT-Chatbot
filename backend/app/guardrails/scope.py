from app.guardrails.matching import PatternSet
from app.guardrails.models import ScopeDecision
from app.guardrails.normalization import normalize_text, security_normalize
from app.guardrails.patterns import BLOCKED_PATTERNS, UNACCENTED_BLOCKED_OVERRIDES
from app.guardrails.security import contains_prompt_injection

_BLOCKED = PatternSet(BLOCKED_PATTERNS, UNACCENTED_BLOCKED_OVERRIDES)


def check_scope(question: str) -> ScopeDecision:
    """Block prompt injection and forbidden tasks before retrieval and generation.

    Questions outside the knowledge base are not rejected here; the confidence
    gate and the LLM system prompt handle them.
    """

    normalized = normalize_text(question)
    if not normalized:
        return ScopeDecision(False, "empty")

    if contains_prompt_injection(security_normalize(question), normalized=True):
        return ScopeDecision(False, "prompt_injection")

    reason = _BLOCKED.first_match(normalized)
    if reason is not None:
        return ScopeDecision(False, reason)

    return ScopeDecision(True, "passed")

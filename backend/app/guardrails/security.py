from app.guardrails.matching import PatternSet
from app.guardrails.normalization import security_normalize
from app.guardrails.patterns import PROMPT_INJECTION_PATTERNS, UNACCENTED_PROMPT_INJECTION_OVERRIDES

_PROMPT_INJECTION = PatternSet(
    (("prompt_injection", pattern) for pattern in PROMPT_INJECTION_PATTERNS),
    UNACCENTED_PROMPT_INJECTION_OVERRIDES,
)


def contains_prompt_injection(value: str, *, normalized: bool = False) -> bool:
    """Return whether untrusted text contains a known prompt-injection pattern."""

    security_text = value if normalized else security_normalize(value)
    return _PROMPT_INJECTION.first_match(security_text) is not None

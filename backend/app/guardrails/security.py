import re

from app.guardrails.normalization import security_normalize
from app.guardrails.patterns import PROMPT_INJECTION_PATTERNS


def contains_prompt_injection(value: str, *, normalized: bool = False) -> bool:
    """Return whether untrusted text contains a known prompt-injection pattern."""

    security_text = value if normalized else security_normalize(value)
    return any(re.search(pattern, security_text) for pattern in PROMPT_INJECTION_PATTERNS)

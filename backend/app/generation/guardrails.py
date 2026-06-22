"""Backward-compatible imports for the guardrails package.

New application code should import from :mod:`app.guardrails`.
"""

from app.guardrails import (
    OUT_OF_SCOPE_ANSWER,
    ScopeDecision,
    check_scope,
    contains_prompt_injection,
    filter_safe_history,
)

__all__ = (
    "OUT_OF_SCOPE_ANSWER",
    "ScopeDecision",
    "check_scope",
    "contains_prompt_injection",
    "filter_safe_history",
)

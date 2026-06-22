from dataclasses import dataclass


@dataclass(frozen=True)
class ScopeDecision:
    """Result of the deterministic domain-scope check."""

    allowed: bool
    reason: str

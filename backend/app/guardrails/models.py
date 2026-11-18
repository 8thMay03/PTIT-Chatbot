from dataclasses import dataclass


@dataclass(frozen=True)
class ScopeDecision:
    """Result of the deterministic input blocklist check."""

    allowed: bool
    reason: str

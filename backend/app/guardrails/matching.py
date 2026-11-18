import re
from collections.abc import Iterable

from app.guardrails.normalization import has_accents, strip_accents


class PatternSet:
    """Labelled regexes matched in two passes.

    Pass 1 runs the original patterns on every text. Pass 2 runs accent-stripped
    copies only when the text carries no diacritics, so accented text keeps the
    exact result of pass 1. ``unaccented_overrides`` are ``(old, new)`` substring
    replacements on the stripped patterns; they narrow branches whose unaccented
    form collides with common words. Each must match exactly once in the set.
    """

    def __init__(
        self,
        patterns: Iterable[tuple[str, str]],
        unaccented_overrides: Iterable[tuple[str, str]] = (),
    ) -> None:
        patterns = tuple(patterns)
        self._accented = tuple((label, re.compile(pattern)) for label, pattern in patterns)
        self._unaccented = tuple(
            (label, re.compile(pattern))
            for label, pattern in _unaccented_patterns(patterns, unaccented_overrides)
        )

    def first_match(self, text: str) -> str | None:
        """Return the label of the first matching pattern, or None."""

        for label, regex in self._accented:
            if regex.search(text):
                return label
        if has_accents(text):
            return None
        for label, regex in self._unaccented:
            if regex.search(text):
                return label
        return None


def _unaccented_patterns(
    patterns: tuple[tuple[str, str], ...],
    overrides: Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    stripped = [(label, strip_accents(pattern)) for label, pattern in patterns]
    for old, new in overrides:
        hits = [index for index, (_, pattern) in enumerate(stripped) if old in pattern]
        if len(hits) != 1 or stripped[hits[0]][1].count(old) != 1:
            raise ValueError(f"Unaccented override {old!r} must match exactly once")
        label, pattern = stripped[hits[0]]
        stripped[hits[0]] = (label, pattern.replace(old, new))
    return stripped

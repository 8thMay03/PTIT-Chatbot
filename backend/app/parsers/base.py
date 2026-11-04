"""Common contract for document parsers, independent of ingestion."""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

# (percent 0-100, human-readable phase message)
ProgressCallback = Callable[[int, str], None]


class DocumentParseError(RuntimeError):
    """A source document cannot be parsed into text."""


class DocumentParser(Protocol):
    """Parsers may also expose variants, default_variant and with_variant(variant)
    to accept "<name>:<variant>" choices (see ParserRegistry.get_parser)."""

    name: str
    extensions: frozenset[str]

    def parse(
        self,
        path: Path,
        *,
        convert: bool = True,
        on_progress: ProgressCallback | None = None,
    ) -> str | None:
        """Return text/Markdown; convert=False must not run expensive conversion."""
        ...

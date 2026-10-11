"""Common contract for document parsers, independent of ingestion."""

from pathlib import Path
from typing import Protocol


class DocumentParseError(RuntimeError):
    """A source document cannot be parsed into text."""


class DocumentParser(Protocol):
    name: str
    extensions: frozenset[str]

    def parse(self, path: Path, *, convert: bool = True) -> str | None:
        """Return text/Markdown; convert=False must not run expensive conversion."""
        ...

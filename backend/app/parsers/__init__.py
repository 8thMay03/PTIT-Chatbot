"""Public document parsing API shared by ingestion, uploads and previews."""

from pathlib import Path

from app.parsers.base import DocumentParseError, DocumentParser
from app.parsers.docling import DoclingParser
from app.parsers.normalize import normalize_markdown
from app.parsers.registry import ParserRegistry
from app.parsers.text import TextParser

registry = ParserRegistry([TextParser(), DoclingParser()])


def get_supported_extensions() -> frozenset[str]:
    return registry.supported_extensions


def read_document_text(
    path: Path, *, convert: bool = True, parser_name: str | None = None
) -> str | None:
    parser = registry.get_parser(path, parser_name=parser_name)
    text = parser.parse(path, convert=convert)
    # One heading hierarchy for every parser, so chunk section paths do not depend on
    # which parser or export produced the Markdown.
    return normalize_markdown(text) if text is not None else None


__all__ = [
    "DocumentParseError",
    "DocumentParser",
    "DoclingParser",
    "ParserRegistry",
    "TextParser",
    "get_supported_extensions",
    "normalize_markdown",
    "read_document_text",
    "registry",
]

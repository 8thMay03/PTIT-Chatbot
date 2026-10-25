"""Public document parsing API shared by ingestion, uploads and previews."""

import logging
from pathlib import Path

from app.parsers.base import DocumentParseError, DocumentParser
from app.parsers.docling import DoclingParser
from app.parsers.llamaparse import LlamaParseParser, llamaparse_available
from app.parsers.normalize import normalize_markdown
from app.parsers.registry import ParserRegistry
from app.parsers.text import TextParser

logger = logging.getLogger(__name__)


def build_registry() -> ParserRegistry:
    # Registration order sets the defaults: Docling stays the PDF/DOCX default and
    # LlamaParse is only an opt-in alternative when configured.
    parsers: list[DocumentParser] = [TextParser(), DoclingParser()]
    if llamaparse_available():
        parsers.append(LlamaParseParser())
    return ParserRegistry(parsers)


registry = build_registry()


def get_supported_extensions() -> frozenset[str]:
    return registry.supported_extensions


def get_parser_name(path: Path, parser_name: str | None = None) -> str:
    """Name of the parser that read_document_text would use for these arguments."""
    return registry.get_parser(path, parser_name=parser_name).name


def resolve_parser_name(path: Path, stored: str | None) -> str | None:
    """Return a document's stored parser while it still handles the file, else None (default)."""
    if not stored or any(item["name"] == stored for item in registry.list_parsers(path)):
        return stored or None
    logger.warning("Parser %r đã lưu cho %s không còn khả dụng; dùng parser mặc định.", stored, path.name)
    return None


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
    "LlamaParseParser",
    "ParserRegistry",
    "TextParser",
    "build_registry",
    "get_parser_name",
    "get_supported_extensions",
    "normalize_markdown",
    "read_document_text",
    "registry",
    "resolve_parser_name",
]

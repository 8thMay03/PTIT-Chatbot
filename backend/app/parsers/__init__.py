"""Public document parsing API shared by ingestion, uploads and previews."""

from pathlib import Path

from app.parsers.base import DocumentParseError, DocumentParser
from app.parsers.docling import DoclingParser
from app.parsers.registry import ParserRegistry
from app.parsers.text import TextParser

registry = ParserRegistry([TextParser(), DoclingParser()])


def get_supported_extensions() -> frozenset[str]:
    return registry.supported_extensions


def read_document_text(
    path: Path, *, convert: bool = True, parser_name: str | None = None
) -> str | None:
    parser = registry.get_parser(path, parser_name=parser_name)
    return parser.parse(path, convert=convert)


__all__ = [
    "DocumentParseError",
    "DocumentParser",
    "DoclingParser",
    "ParserRegistry",
    "TextParser",
    "get_supported_extensions",
    "read_document_text",
    "registry",
]

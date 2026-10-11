"""Compatibility imports; new parser implementations belong in app.parsers."""

from app.parsers import DocumentParseError as DocumentConversionError
from app.parsers import get_supported_extensions, read_document_text
from app.parsers.docling import DOCLING_EXTENSIONS, convert_with_docling
from app.parsers.text import TEXT_EXTENSIONS

SUPPORTED_EXTENSIONS = get_supported_extensions()

__all__ = [
    "DocumentConversionError",
    "DOCLING_EXTENSIONS",
    "SUPPORTED_EXTENSIONS",
    "TEXT_EXTENSIONS",
    "convert_with_docling",
    "read_document_text",
]

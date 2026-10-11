import logging
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.converters import (
    SUPPORTED_EXTENSIONS,
    DocumentConversionError,
    read_document_text,
)

logger = logging.getLogger(__name__)

__all__ = ("SUPPORTED_EXTENSIONS", "SourceDocument", "load_documents")


@dataclass(frozen=True)
class SourceDocument:
    path: Path
    text: str


def load_documents(data_dir: Path) -> list[SourceDocument]:
    if not data_dir.exists():
        return []

    documents: list[SourceDocument] = []
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            text = read_document_text(path)
        except DocumentConversionError as exc:
            # One unreadable file must not abort a full knowledge-base rebuild.
            logger.warning("Skipping %s: %s", path, exc)
            continue
        if text and text.strip():
            documents.append(SourceDocument(path=path, text=text))

    return documents

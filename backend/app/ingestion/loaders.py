from dataclasses import dataclass
from pathlib import Path

from app.ingestion.converters import (
    SUPPORTED_EXTENSIONS,
    DocumentConversionError,
    read_document_text,
)

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
        except (DocumentConversionError, OSError, UnicodeError) as exc:
            # A partial result would delete failed documents during replacement.
            raise DocumentConversionError(f"Không parse được tài liệu {path.name}: {exc}") from exc
        if not text or not text.strip():
            raise DocumentConversionError(f"{path.name} không có nội dung văn bản.")
        documents.append(SourceDocument(path=path, text=text))

    return documents

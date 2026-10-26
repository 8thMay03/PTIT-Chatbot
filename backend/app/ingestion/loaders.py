from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.parsers import (
    DocumentParseError,
    get_parser_name,
    get_supported_extensions,
    read_document_text,
    resolve_parser_name,
)

SUPPORTED_EXTENSIONS = get_supported_extensions()  # Legacy import compatibility.
__all__ = ("SUPPORTED_EXTENSIONS", "SourceDocument", "load_documents")


@dataclass(frozen=True)
class SourceDocument:
    path: Path
    text: str
    # Parser that produced text; None when the caller did not track it.
    parser_name: str | None = None
    # text is a manual edit of the parser output rather than the output itself.
    markdown_edited: bool = False


def load_documents(
    data_dir: Path,
    parser_for: Callable[[Path], str | None] | None = None,
    edited_text_for: Callable[[Path], str | None] | None = None,
) -> list[SourceDocument]:
    """Read every supported file.

    parser_for returns a document's stored parser choice; edited_text_for returns its
    manually edited Markdown, which is kept instead of parsing the file again.
    """
    if not data_dir.exists():
        return []

    documents: list[SourceDocument] = []
    supported_extensions = get_supported_extensions()
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in supported_extensions:
            continue
        parser_name = resolve_parser_name(path, parser_for(path) if parser_for else None)
        edited_text = edited_text_for(path) if edited_text_for else None
        if edited_text is not None:
            documents.append(
                SourceDocument(
                    path=path,
                    text=edited_text,
                    parser_name=get_parser_name(path, parser_name),
                    markdown_edited=True,
                )
            )
            continue
        try:
            text = read_document_text(path, parser_name=parser_name)
        except (DocumentParseError, OSError, UnicodeError) as exc:
            # A partial result would delete failed documents during replacement.
            raise DocumentParseError(f"Không parse được tài liệu {path.name}: {exc}") from exc
        if not text or not text.strip():
            raise DocumentParseError(f"{path.name} không có nội dung văn bản.")
        documents.append(SourceDocument(path=path, text=text, parser_name=get_parser_name(path, parser_name)))

    return documents

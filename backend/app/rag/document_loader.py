from dataclasses import dataclass
from pathlib import Path


SUPPORTED_EXTENSIONS = {".md", ".txt"}


@dataclass(frozen=True)
class SourceDocument:
    path: Path
    text: str


def load_documents(data_dir: Path) -> list[SourceDocument]:
    if not data_dir.exists():
        return []

    documents: list[SourceDocument] = []
    for path in sorted(data_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            documents.append(SourceDocument(path=path, text=path.read_text(encoding="utf-8")))

    return documents

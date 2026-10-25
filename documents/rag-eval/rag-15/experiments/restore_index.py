"""RAG-15: khôi phục index local về trạng thái trước task (2 tài liệu, cùng ID).

Chạy từ backend/:
    python ../documents/rag-eval/rag-15/experiments/restore_index.py

Trạng thái gốc (2026-10-25, trước RAG-15):
- `19a636282f29…` data/processed/Sổ tay sinh viên D26 _1_ _1_.md — 1203 chunk (index RAG-06).
  RAG-06 ingest bằng đường dẫn tương đối nên ID/chunk ID tính từ "../data/...", rồi
  GET /documents/{id} tự đồng bộ source_path về "data/...". Tái hiện đúng hai bước đó.
- `e0997dd268c1…` data/Sổ tay sinh viên D26 _1_.pdf — 977 chunk, Docling (bản upload qua app).
"""

import sys

sys.path.insert(0, ".")

from pathlib import Path

from sqlalchemy import func, select

from app.db.models import Chunk, Document
from app.db.session import SessionLocal
from app.ingestion import pipeline
from app.ingestion.loaders import SourceDocument
from app.parsers import read_document_text

MD = Path("../data/processed/Sổ tay sinh viên D26 _1_ _1_.md")
PDF = Path("../data/Sổ tay sinh viên D26 _1_.pdf").resolve()
MD_SOURCE_PATH = "data/processed/Sổ tay sinh viên D26 _1_ _1_.md"


def main() -> None:
    documents = [
        SourceDocument(path=MD, text=read_document_text(MD), parser_name="text"),
        SourceDocument(path=PDF, text=read_document_text(PDF, parser_name="docling"), parser_name="docling"),
    ]
    pipeline.load_documents = lambda _data_dir, **_kwargs: documents
    print(pipeline.ingestion_pipeline.ingest_documents())

    with SessionLocal() as session:
        document = session.scalar(select(Document).where(Document.source_path == MD.as_posix()))
        document.source_path = MD_SOURCE_PATH
        session.commit()
        for document in session.scalars(select(Document)):
            chunks = session.scalar(
                select(func.count()).select_from(Chunk).where(Chunk.document_id == document.id)
            )
            print(document.id[:12], document.source_path, chunks, (document.document_metadata or {}).get("parser"))


if __name__ == "__main__":
    main()

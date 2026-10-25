"""Scratch RAG-06: re-ingest chỉ bản D26 processed (không commit, chạy một lần)."""

import sys

sys.path.insert(0, ".")

from pathlib import Path

from app.ingestion import pipeline
from app.ingestion.loaders import SourceDocument
from app.parsers import read_document_text

DOC = Path("../data/processed/Sổ tay sinh viên D26 _1_ _1_.md")


def load_single(_data_dir):
    return [SourceDocument(path=DOC, text=read_document_text(DOC))]


pipeline.load_documents = load_single
result = pipeline.ingestion_pipeline.ingest_documents()
print(result)

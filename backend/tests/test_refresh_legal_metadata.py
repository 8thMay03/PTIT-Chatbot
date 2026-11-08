"""scripts.refresh_legal_metadata: chỉ gộp khóa legal_* vào metadata, không chunk lại/embedding."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.models import Chunk
from app.embeddings.models import HashEmbeddingModel
from app.ingestion.legal_units import LEGAL_METADATA_KEYS
from app.ingestion.pipeline import IngestionPipeline
from scripts import refresh_legal_metadata
from tests.test_search_text import NullVectorStore, _memory_engine, _patch_pipeline_sessions

_LEGAL_DOC = (
    "# Quy chế\n\n## Thủ tục\n\n1. Nộp đơn.\n\n2. Nhận kết quả.\n\n"
    "## Điều 5. Học phí\n\n1. Học phí thu theo học kỳ.\n\n"
    "2. Sinh viên được miễn học phí khi:\n\na) Thuộc hộ nghèo;\n\nb) Là con liệt sĩ.\n"
)


def _indexed_without_legal_metadata(tmp_path: Path, monkeypatch):
    """Index một tài liệu rồi xóa khóa legal_* như chunk index trước RAG-22."""
    engine = _memory_engine()
    _patch_pipeline_sessions(monkeypatch, engine)
    pipeline = IngestionPipeline(embedding_model=HashEmbeddingModel(), vector_store=NullVectorStore())
    source = tmp_path / "quy-che.md"
    source.write_text(_LEGAL_DOC, encoding="utf-8")
    pipeline.chunk_document(pipeline.parse_path(source, dataset_id="ds-test")["id"])

    factory = sessionmaker(bind=engine, future=True)
    with factory() as session:
        for chunk in session.scalars(select(Chunk)):
            chunk.chunk_metadata = {
                key: value for key, value in chunk.chunk_metadata.items() if key not in LEGAL_METADATA_KEYS
            }
        session.commit()
    return factory


def _snapshot(factory) -> dict[str, tuple[str, str, list[float], dict]]:
    with factory() as session:
        return {
            chunk.id: (chunk.text, chunk.search_text, list(chunk.embedding), dict(chunk.chunk_metadata))
            for chunk in session.scalars(select(Chunk))
        }


def test_dry_run_reports_without_writing(tmp_path: Path, monkeypatch, capsys) -> None:
    factory = _indexed_without_legal_metadata(tmp_path, monkeypatch)
    before = _snapshot(factory)

    assert refresh_legal_metadata.main([], session_factory=factory) == 0

    assert _snapshot(factory) == before
    output = capsys.readouterr().out
    assert "Dry-run" in output
    assert "cần ghi legal_*" in output


def test_apply_merges_only_legal_keys(tmp_path: Path, monkeypatch) -> None:
    factory = _indexed_without_legal_metadata(tmp_path, monkeypatch)
    before = _snapshot(factory)

    assert refresh_legal_metadata.main(["--apply"], session_factory=factory) == 0

    after = _snapshot(factory)
    assert after.keys() == before.keys()
    by_heading: dict[str, list[dict]] = {}
    for chunk_id, (text, search_text, embedding, metadata) in after.items():
        old_text, old_search_text, old_embedding, old_metadata = before[chunk_id]
        assert (text, search_text, embedding) == (old_text, old_search_text, old_embedding)
        assert {key: value for key, value in metadata.items() if key not in LEGAL_METADATA_KEYS} == old_metadata
        assert set(LEGAL_METADATA_KEYS) <= set(metadata)
        by_heading.setdefault(metadata["heading"], []).append(metadata)

    assert all(item["legal_article"] == "Điều 5. Học phí" for item in by_heading["Điều 5. Học phí"])
    assert any(item["legal_clauses"] for item in by_heading["Điều 5. Học phí"])
    assert all(item["legal_clauses"] == [] for item in by_heading["Thủ tục"])

    # Chạy lại không còn gì để ghi.
    with factory() as session:
        assert refresh_legal_metadata.plan_refresh(session).updates == {}


def test_document_with_drifted_text_is_skipped(tmp_path: Path, monkeypatch) -> None:
    factory = _indexed_without_legal_metadata(tmp_path, monkeypatch)
    with factory() as session:
        chunk = session.scalars(select(Chunk)).first()
        chunk.text = chunk.text + " (đã sửa tay)"
        session.commit()
    before = _snapshot(factory)

    assert refresh_legal_metadata.main(["--apply"], session_factory=factory) == 1

    assert _snapshot(factory) == before

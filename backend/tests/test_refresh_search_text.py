"""scripts.refresh_search_text: chỉ cập nhật search_text, không chunk lại/embedding."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import Chunk
from app.embeddings.models import HashEmbeddingModel
from app.ingestion.chunker import compose_search_text
from app.ingestion.pipeline import IngestionPipeline
from scripts import refresh_search_text
from tests.test_search_text import NullVectorStore, _memory_engine, _patch_pipeline_sessions

_TABLE_DOC = (
    "# Liên hệ\n\nLãnh đạo khoa và các bộ môn.\n\n"
    "|ĐƠN VỊ|HỌ VÀ TÊN|CHỨC VỤ|\n|-|-|-|\n"
    "|Lãnh đạo Khoa|GS.TS. Phạm Ngọc Anh|Trưởng khoa|\n"
    "||TS. Lê Văn Ngọc|Phó trưởng khoa|\n"
)


def _indexed_with_old_search_text(tmp_path: Path, monkeypatch):
    """Index một tài liệu bảng rồi đưa search_text về dạng cũ (header + text thô)."""
    engine = _memory_engine()
    _patch_pipeline_sessions(monkeypatch, engine)
    pipeline = IngestionPipeline(embedding_model=HashEmbeddingModel(), vector_store=NullVectorStore())
    source = tmp_path / "lien-he.md"
    source.write_text(_TABLE_DOC, encoding="utf-8")
    pipeline.chunk_document(pipeline.parse_path(source, dataset_id="ds-test")["id"])

    factory = sessionmaker(bind=engine, future=True)
    with factory() as session:
        for chunk in session.scalars(select(Chunk)):
            chunk.search_text = compose_search_text(
                "lien-he", chunk.chunk_metadata["section_path"], chunk.text
            )
        session.commit()
    return factory


def _snapshot(factory) -> dict[str, tuple[str, str, list[float]]]:
    with factory() as session:
        return {
            chunk.id: (chunk.text, chunk.search_text, list(chunk.embedding))
            for chunk in session.scalars(select(Chunk))
        }


def test_dry_run_reports_without_writing(tmp_path: Path, monkeypatch, capsys) -> None:
    factory = _indexed_with_old_search_text(tmp_path, monkeypatch)
    before = _snapshot(factory)

    assert refresh_search_text.main([], session_factory=factory) == 0

    assert _snapshot(factory) == before
    assert "Dry-run" in capsys.readouterr().out


def test_apply_updates_only_search_text(tmp_path: Path, monkeypatch) -> None:
    factory = _indexed_with_old_search_text(tmp_path, monkeypatch)
    before = _snapshot(factory)

    assert refresh_search_text.main(["--apply"], session_factory=factory) == 0

    after = _snapshot(factory)
    assert after.keys() == before.keys()
    table_ids = [chunk_id for chunk_id, (text, _, _) in before.items() if "|-|" in text]
    assert table_ids
    for chunk_id, (text, search_text, embedding) in after.items():
        assert text == before[chunk_id][0]
        assert embedding == before[chunk_id][2]
        if chunk_id in table_ids:
            assert "CHỨC VỤ: Trưởng khoa" in search_text
            assert "ĐƠN VỊ: Lãnh đạo Khoa; HỌ VÀ TÊN: TS. Lê Văn Ngọc" in search_text
            assert "|Lãnh đạo Khoa|" not in search_text

    # Chạy lại không còn gì để đổi.
    with factory() as session:
        assert refresh_search_text.plan_refresh(session).updates == {}


def test_document_with_drifted_text_is_skipped(tmp_path: Path, monkeypatch) -> None:
    factory = _indexed_with_old_search_text(tmp_path, monkeypatch)
    with factory() as session:
        chunk = session.scalars(select(Chunk)).first()
        chunk.text = chunk.text + " (đã sửa tay)"
        session.commit()
    before = _snapshot(factory)

    assert refresh_search_text.main(["--apply"], session_factory=factory) == 1

    assert _snapshot(factory) == before


def test_refuses_when_embedding_uses_search_text(tmp_path: Path, monkeypatch) -> None:
    factory = _indexed_with_old_search_text(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "embedding_input_field", "search_text")
    before = _snapshot(factory)

    assert refresh_search_text.main(["--apply"], session_factory=factory) == 2

    assert _snapshot(factory) == before

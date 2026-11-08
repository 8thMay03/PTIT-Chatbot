"""RAG-22 S-03: Điều/Khoản/Điểm tính lúc chunking và đi qua vector → BM25 → parent-child → citation."""

from contextlib import contextmanager
from types import SimpleNamespace

from app.db.models import Chunk as ChunkRow
from app.generation.citations import public_citations
from app.ingestion.chunker import split_parent_child, split_text
from app.ingestion.pipeline import _chunk_records
from app.retrieval import bm25 as bm25_module
from app.retrieval.parent_child import collapse_parent_results
from app.vectordb.pgvector_store import _format_chunk_context

POINT_TEXT = "Sinh viên thuộc diện này khi không hoàn thành nghĩa vụ học tập theo quy định của Học viện."

ARTICLE_DOC = "\n\n".join(
    [
        "### Điều 33. Cảnh báo kết quả học tập",
        "1. Việc cảnh báo kết quả học tập được thực hiện theo từng học kỳ chính.",
        "2. Sinh viên bị cảnh báo kết quả học tập nếu thuộc một trong các trường hợp:",
        *(f"{letter}) {POINT_TEXT}" for letter in "abcdef"),
        "3. Sinh viên bị cảnh báo được thông báo bằng văn bản.",
        "### Thủ tục xin bảng điểm",
        "1. Nộp đơn tại bộ phận một cửa của Học viện, ghi rõ số lượng bản cần cấp.",
        "2) Nhận phiếu hẹn và quay lại nhận bảng điểm sau ba ngày làm việc.",
        "a) Bản sao căn cước công dân còn hiệu lực theo quy định hiện hành.",
    ]
)


def _parent_child_chunks():
    return split_parent_child(
        ARTICLE_DOC, parent_size=400, parent_overlap=0, child_size=260, child_overlap=0, min_child_size=60
    )


def test_child_starting_mid_clause_inherits_open_clause() -> None:
    chunks = [chunk for chunk in _parent_child_chunks() if chunk.heading.startswith("Điều 33")]
    assert len({chunk.parent_index for chunk in chunks}) > 1

    for chunk in chunks:
        assert chunk.legal_article == "Điều 33. Cảnh báo kết quả học tập"
    mid_clause = [chunk for chunk in chunks if chunk.text.split("\n\n")[1].startswith(("c)", "d)", "e)", "f)"))]
    assert mid_clause, "fixture phải có child bắt đầu giữa Khoản 2"
    for chunk in mid_clause:
        assert chunk.legal_clauses[0] == "2"
    assert chunks[-1].legal_clauses[-1] == "3"


def test_non_article_section_has_no_clauses_or_points() -> None:
    chunks = [chunk for chunk in _parent_child_chunks() if chunk.heading == "Thủ tục xin bảng điểm"]

    assert chunks
    for chunk in chunks:
        assert chunk.legal_article is None
        assert chunk.legal_clauses == ()
        assert chunk.legal_points == ()


def test_split_text_path_also_carries_legal_units() -> None:
    chunks = split_text(ARTICLE_DOC, chunk_size=260, chunk_overlap=0)
    article_chunks = [chunk for chunk in chunks if chunk.heading.startswith("Điều 33")]

    assert len(article_chunks) > 1
    assert all(chunk.legal_article for chunk in article_chunks)
    assert any(chunk.legal_clauses[:1] == ("2",) and "1. " not in chunk.text for chunk in article_chunks)
    assert all(chunk.legal_clauses == () for chunk in chunks if chunk.heading == "Thủ tục xin bảng điểm")


def test_chunk_records_write_legal_metadata(monkeypatch) -> None:
    from app.ingestion import pipeline

    monkeypatch.setattr(pipeline, "_split_document", lambda text: _parent_child_chunks())
    records, _ = _chunk_records("doc1", "data/so-tay.md", "Sổ tay", ARTICLE_DOC)

    for record in records:
        metadata = record.metadata
        assert set(metadata) >= {"legal_article", "legal_clauses", "legal_points"}
        assert isinstance(metadata["legal_clauses"], list)
    procedure = [record for record in records if record.metadata["heading"] == "Thủ tục xin bảng điểm"]
    assert procedure and all(record.metadata["legal_clauses"] == [] for record in procedure)


def _row(metadata: dict) -> ChunkRow:
    return ChunkRow(id="c1", document_id="d1", chunk_index=0, text="b) Nội dung.", search_text="", chunk_metadata=metadata)


LEGAL = {"legal_article": "Điều 33. Cảnh báo", "legal_clauses": ["2"], "legal_points": ["b"]}


def test_vector_context_copies_legal_metadata_only_when_present() -> None:
    with_legal = _format_chunk_context(_row({"heading": "Điều 33. Cảnh báo", **LEGAL}), 0.5)
    legacy = _format_chunk_context(_row({"heading": "Điều 33. Cảnh báo"}), 0.5)

    assert {key: with_legal[key] for key in LEGAL} == LEGAL
    assert not set(LEGAL) & set(legacy)


def test_bm25_snapshot_copies_legal_metadata_only_when_present(monkeypatch) -> None:
    rows = [
        (_row({"heading": "Điều 33. Cảnh báo", **LEGAL}), "ds1"),
        (_row({"heading": "Điều 33. Cảnh báo"}), "ds1"),
    ]

    @contextmanager
    def fake_session():
        yield SimpleNamespace(execute=lambda statement: SimpleNamespace(all=lambda: rows))

    monkeypatch.setattr(bm25_module, "SessionLocal", fake_session)
    snapshots = bm25_module.BM25Search._load_chunks()

    assert {key: snapshots[0][key] for key in LEGAL} == LEGAL
    assert not set(LEGAL) & set(snapshots[1])


def _child(chunk_id: str, score: float, text: str, **legal) -> dict:
    return {
        "chunk_id": chunk_id,
        "parent_id": "p1",
        "heading": "Điều 33. Cảnh báo",
        "section_path": "Quy chế > Điều 33. Cảnh báo",
        "source_name": "so-tay.md",
        "text": text,
        "parent_text": "## Điều 33. Cảnh báo\n\n1. A.\n\n2. B:\n\na) x\n\nb) y",
        "score": score,
        **legal,
    }


def test_parent_collapse_takes_legal_metadata_from_evidence_child() -> None:
    results = collapse_parent_results(
        [
            _child("c0", 0.4, "1. A.", legal_article="Điều 33. Cảnh báo", legal_clauses=["1"], legal_points=[]),
            _child("c1", 0.9, "b) y", legal_article="Điều 33. Cảnh báo", legal_clauses=["2"], legal_points=["b"]),
        ],
        top_k=1,
    )

    assert results[0]["evidence_text"] == "b) y"
    assert results[0]["legal_clauses"] == ["2"]
    assert results[0]["legal_points"] == ["b"]
    assert public_citations(results)[0]["locator"] == "Điều 33. Cảnh báo — Khoản 2; Điểm b"


def test_parent_collapse_drops_legal_metadata_when_evidence_child_has_none() -> None:
    results = collapse_parent_results(
        [
            _child("c0", 0.4, "1. A.", legal_article="Điều 33. Cảnh báo", legal_clauses=["1"], legal_points=[]),
            _child("c1", 0.9, "b) y"),
        ],
        top_k=1,
    )

    assert "legal_clauses" not in results[0]
    # Đường dự phòng: không biết Khoản đang mở, chỉ còn Điểm.
    assert public_citations(results)[0]["locator"] == "Điều 33. Cảnh báo — Điểm b"


def test_citation_prefers_metadata_even_when_empty() -> None:
    context = {
        "source_name": "so-tay.md",
        "heading": "Điều 33. Cảnh báo",
        "section_path": "Quy chế > Điều 33. Cảnh báo",
        "text": "1. Nội dung.",
        "legal_article": None,
        "legal_clauses": [],
        "legal_points": [],
    }

    citation = public_citations([context])[0]

    assert citation["article"] is None
    assert citation["clauses"] == []
    assert citation["locator"] == "Điều 33. Cảnh báo"

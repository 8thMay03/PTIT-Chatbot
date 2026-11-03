from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.db.repositories import ChunkRecord, DocumentRecord, ensure_default_dataset, save_parsed_document, create_dataset, replace_document_chunks
from app.embeddings.models import HashEmbeddingModel
from app.retrieval.bm25 import BM25Search, invalidate_bm25_cache
from app.retrieval.retriever import Retriever
from app.vectordb.pgvector_store import PgVectorStore


def _session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with factory() as session:
        ensure_default_dataset(session)
        session.commit()
    return factory


def _seed(factory, docs):
    embedding = HashEmbeddingModel()
    with factory() as session:
        for dataset_id, doc_id, text in docs:
            record = DocumentRecord(
                id=doc_id, dataset_id=dataset_id, source_path=f"data/{doc_id}.md",
                title=doc_id, file_type="md", content_hash="h-" + doc_id,
                metadata={"size_bytes": len(text)}, parsed_text=text,
            )
            stored = save_parsed_document(session, record)
            chunks = [
                ChunkRecord(
                    id=f"{doc_id}::chunk-{i}", document_id=doc_id, chunk_index=i,
                    text=part, vector_id=f"{doc_id}::chunk-{i}", search_text=part,
                    metadata={"source": record.source_path, "source_name": f"{doc_id}.md", "document_id": doc_id, "chunk_id": f"{doc_id}::chunk-{i}"},
                )
                for i, part in enumerate(text.split("\n\n"))
            ]
            replace_document_chunks(session, stored, chunks)
        session.commit()
    # Embed vào DB sqlite (pgvector fallback đọc cột embedding).
    store = PgVectorStore(session_factory=factory)
    with factory() as session:
        from app.db.models import Chunk
        from sqlalchemy import select

        rows = list(session.scalars(select(Chunk)))
        payloads = [{"id": c.id, "text": c.text, "search_text": c.search_text, "metadata": c.chunk_metadata} for c in rows]
    vectors = embedding.embed([p["search_text"] for p in payloads]) if payloads else []
    store.add(payloads, vectors)
    invalidate_bm25_cache()
    return store


def test_vector_and_bm25_filter_disabled_dataset():
    factory = _session_factory()
    with factory() as session:
        ds_on = create_dataset(session, "Bật")
        ds_on2 = create_dataset(session, "Bật 2")
        ds_on3 = create_dataset(session, "Bật 3")
        ds_off = create_dataset(session, "Tắt")
        session.commit()
        on_id, on2_id, on3_id, off_id = ds_on.id, ds_on2.id, ds_on3.id, ds_off.id
        from app.db.repositories import update_dataset

        update_dataset(session, off_id, enabled=False)
        session.commit()
    # BM25 với N=2 cho IDF=0 nên cần ≥3 doc đang bật để điểm >0.
    store = _seed(factory, [
        (on_id, "d-on", "học phí tín chỉ PTIT"),
        (on2_id, "d-on2", "quy chế đào tạo tín chỉ"),
        (on3_id, "d-on3", "thư viện giáo trình"),
        (off_id, "d-off", "học bổng ký túc xá PTIT"),
    ])
    embedding = HashEmbeddingModel()
    query_vec = embedding.embed(["học bổng"])[0]
    # Không lọc: chỉ thấy dataset bật.
    assert any(r["document_id"] == "d-on" for r in store.search(query_vec, top_k=5))
    assert not any(r["document_id"] == "d-off" for r in store.search(query_vec, top_k=5))
    # Lọc显式 tới dataset tắt → rỗng vì giao với tập đang bật.
    assert store.search(query_vec, top_k=5, dataset_ids=[off_id]) == []
    # BM25 cùng quy tắc.
    import app.retrieval.bm25 as bm25_module

    monkey_factory = factory
    orig = bm25_module.SessionLocal
    bm25_module.SessionLocal = monkey_factory
    try:
        search = BM25Search()
        assert any(r["document_id"] == "d-on" for r in search.search("học phí", top_k=5))
        assert not any(r["document_id"] == "d-off" for r in search.search("học phí", top_k=5))
        assert search.search("học bổng", top_k=5, dataset_ids=[off_id]) == []
    finally:
        bm25_module.SessionLocal = orig
        invalidate_bm25_cache()


class _SavepointSession:
    """Ghi lại câu lệnh và savepoint; tùy chọn ném lỗi DB như pgvector < 0.8."""

    def __init__(self, error=None):
        from contextlib import contextmanager

        self.error = error
        self.statements = []
        self.savepoints = []

        @contextmanager
        def begin_nested():
            self.savepoints.append("open")
            try:
                yield
            except Exception:
                self.savepoints[-1] = "rolled_back"
                raise
            self.savepoints[-1] = "released"

        self.begin_nested = begin_nested

    def execute(self, statement):
        self.statements.append(statement)
        if self.error is not None:
            raise self.error


def test_iterative_scan_uses_text_inside_savepoint():
    from sqlalchemy.exc import ProgrammingError
    from sqlalchemy.sql.elements import TextClause

    from app.vectordb.pgvector_store import _enable_iterative_scan

    ok = _SavepointSession()
    assert _enable_iterative_scan(ok) is True
    [statement] = ok.statements
    assert isinstance(statement, TextClause)
    assert str(statement) == "SET LOCAL hnsw.iterative_scan = relaxed_order"
    assert ok.savepoints == ["released"]

    # pgvector cũ từ chối tham số: chỉ savepoint bị rollback, search tiếp tục.
    old = _SavepointSession(error=ProgrammingError("SET LOCAL", {}, Exception("unrecognized parameter")))
    assert _enable_iterative_scan(old) is False
    assert old.savepoints == ["rolled_back"]


def test_retriever_respects_dataset_ids():
    factory = _session_factory()
    with factory() as session:
        ds = create_dataset(session, "Riêng")
        session.commit()
        ds_id = ds.id
    store = _seed(factory, [(ds_id, "d1", "học phí PTIT"), ("default", "d2", "thư viện PTIT")])
    import app.retrieval.bm25 as bm25_module

    bm25_module.SessionLocal = factory
    try:
        retriever = Retriever(embedding_model=HashEmbeddingModel(), vector_store=store, keyword_search=BM25Search())
        all_docs = {c["document_id"] for c in retriever.retrieve("PTIT", top_k=5)}
        assert "d1" in all_docs and "d2" in all_docs
        only = {c["document_id"] for c in retriever.retrieve("PTIT", top_k=5, dataset_ids=[ds_id])}
        assert only == {"d1"}
    finally:
        bm25_module.SessionLocal = factory
        invalidate_bm25_cache()

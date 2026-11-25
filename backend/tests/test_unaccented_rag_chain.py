"""Câu hỏi không dấu qua gate mà không cần LLM sửa câu (task unaccented-query-retrieval, AC-06).

Chạy ``RagChain`` với ``Retriever`` thật: BM25 (cả chỉ mục bỏ dấu) trên kho nhỏ, embedding và
vector store giả không trả kết quả, nên mọi tín hiệu đến từ BM25.
"""

import pytest

from app.core.config import settings
from app.generation.query_corrector import QueryCorrector
from app.generation.query_rewriter import VietnameseQueryRewriter
from app.generation.rag_chain import RagChain
from app.llm import LLMBudget
from app.retrieval.bm25 import BM25Search
from app.retrieval.retriever import Retriever

QUESTION = "hoc phi mot tin chi la bao nhieu"
CORPUS = [
    "Học phí một tín chỉ là bao nhiêu? Học phí một tín chỉ năm học này là 500.000 đồng.",
    "Thư viện mở cửa từ 7 giờ đến 21 giờ các ngày trong tuần.",
    "Sinh viên đăng ký học phần trên cổng thông tin đào tạo trước mỗi học kỳ.",
    "Ký túc xá có phòng 4 người và phòng 6 người.",
    "Điều kiện xét tốt nghiệp gồm hoàn thành chương trình và chuẩn đầu ra tiếng Anh.",
    "Câu lạc bộ âm nhạc tuyển thành viên vào đầu năm học.",
]


class _ZeroEmbedding:
    def embed_query(self, texts: list[str]) -> list[list[float]]:
        return [[0.0, 0.0, 0.0] for _ in texts]


class _NoVectorStore:
    def search(self, vector, top_k: int, dataset_ids=None, **kwargs) -> list[dict]:
        return []


class _FailingLLM:
    timeout = 30.0

    def __init__(self) -> None:
        self.calls = 0

    def is_configured(self) -> bool:
        return True

    def generate(self, messages, **kwargs) -> str:
        self.calls += 1
        raise RuntimeError("upstream 503")


class _SingleQuery:
    def generate(self, query: str, budget=None) -> list[str]:
        return [query]


@pytest.fixture
def unaccented_settings(monkeypatch) -> None:
    for name, value in {
        "query_correction_enabled": True,
        "query_rewrite_use_llm": False,
        "reranker_enabled": False,
        "guardrail_scope_enabled": True,
        "embedding_model": "text-embedding-3-small",
        "retrieval_min_vector_score": None,
        "retrieval_min_bm25_norm_score": 0.25,
        "retrieval_min_bm25_folded_norm_score": 0.40,
        "retrieval_min_rerank_score": None,
        "hybrid_vector_weight": 0.8,
        "hybrid_folded_vector_weight": 0.3,
    }.items():
        monkeypatch.setattr(settings, name, value)


def _chain(monkeypatch, llm: _FailingLLM) -> RagChain:
    keyword_search = BM25Search()
    chunks = [
        {"chunk_id": f"c{index}", "chunk_index": index, "parent_id": f"p{index}", "text": text}
        for index, text in enumerate(CORPUS)
    ]
    monkeypatch.setattr(keyword_search, "_load_chunks", lambda: chunks)
    retriever = Retriever(
        embedding_model=_ZeroEmbedding(), vector_store=_NoVectorStore(), keyword_search=keyword_search
    )
    return RagChain(
        retriever_=retriever,
        query_rewriter=VietnameseQueryRewriter(query_corrector=QueryCorrector(llm)),
        multi_query_generator=_SingleQuery(),
    )


@pytest.mark.parametrize(
    ("budget", "reason", "llm_calls"),
    [
        (None, "llm_error", 1),
        (LLMBudget(0), "skipped_budget", 0),
    ],
)
def test_unaccented_question_passes_gate_when_correction_llm_is_unavailable(
    unaccented_settings, monkeypatch, budget, reason, llm_calls
) -> None:
    llm = _FailingLLM()

    result = _chain(monkeypatch, llm).retrieve_context(QUESTION, budget=budget)

    debug = result["retrieval_debug"]
    assert debug["query_corrected"] is False
    assert debug["correction_reason"] == reason
    assert llm.calls == llm_calls
    assert debug["strong_context"] is True
    assert debug["confidence"]["reason"] == "passed"
    assert debug["confidence"]["signals"]["bm25_folded_norm"] >= 0.40
    assert debug["confidence"]["signals"]["bm25_norm"] < 0.25
    assert debug["confidence"]["thresholds"]["min_bm25_folded_norm_score"] == 0.40
    top = debug["selected_chunks"][0]
    assert top["chunk_id"] == "c0"
    assert top["bm25_index"] == "folded"
    assert top["bm25_folded_norm_score"] >= 0.40


def test_unaccented_question_is_refused_without_folded_signal(unaccented_settings, monkeypatch) -> None:
    # Đối chứng: tắt ngưỡng bỏ dấu thì câu không dấu lại bị gate từ chối như trước task.
    monkeypatch.setattr(settings, "retrieval_min_bm25_folded_norm_score", None)

    result = _chain(monkeypatch, _FailingLLM()).retrieve_context(QUESTION)

    debug = result["retrieval_debug"]
    assert debug["strong_context"] is False
    assert debug["confidence"]["reason"] == "below_bm25_norm"

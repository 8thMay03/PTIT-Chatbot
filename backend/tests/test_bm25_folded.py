"""Chỉ mục BM25 bỏ dấu cho câu hỏi không dấu hoặc thiếu dấu (task unaccented-query-retrieval)."""

import pytest

from app.core.config import settings
from app.retrieval.bm25 import BM25Search, invalidate_bm25_cache, rank_bm25
from app.retrieval.hybrid import reciprocal_rank_fusion
from app.retrieval.multi_query import fuse_multi_query_results
from app.retrieval.parent_child import collapse_parent_results
from app.retrieval.reranker import heuristic_rerank

TEXTS = [
    "thông tin thư viện mở cửa buổi sáng",
    "lịch học của sinh viên theo tuần",
    "quy định về trang phục khi đến lớp",
    "hướng dẫn đăng nhập hệ thống quản lý",
    "câu lạc bộ âm nhạc tuyển thành viên",
    "mức học phí một tín chỉ năm học mới",
    "đăng ký học phần trên cổng thông tin đào tạo",
    "giới thiệu học viện công nghệ bưu chính viễn thông",
]
TUITION = "5"
REGISTRATION = "6"


def _search_over(monkeypatch, texts: list[str] = TEXTS, dataset_ids: list[str] | None = None) -> BM25Search:
    search = BM25Search()
    chunks = [
        {
            "chunk_id": str(index),
            "chunk_index": index,
            "text": text,
            "dataset_id": dataset_ids[index] if dataset_ids else "d1",
        }
        for index, text in enumerate(texts)
    ]
    monkeypatch.setattr(search, "_load_chunks", lambda: chunks)
    return search


def test_unaccented_query_matches_accented_chunk_through_folded_index(monkeypatch) -> None:
    search = _search_over(monkeypatch)

    results = search.search("hoc phi mot tin chi", top_k=3)

    top = results[0]
    assert top["chunk_id"] == TUITION
    assert top["bm25_index"] == "folded"
    assert top["bm25_folded_norm_score"] >= 0.25
    # Chỉ mục có dấu gần như không khớp câu không dấu: điểm có dấu vẫn được báo để gate đọc.
    assert top["bm25_norm_score"] < 0.25
    assert all(0.0 <= result["bm25_folded_norm_score"] <= 1.0 for result in results)


def test_folded_index_maps_d_stroke(monkeypatch) -> None:
    search = _search_over(monkeypatch)

    top = search.search("dang ky hoc phan", top_k=1)[0]

    assert top["chunk_id"] == REGISTRATION
    assert top["bm25_index"] == "folded"


def test_accented_query_above_threshold_keeps_accented_ranking(monkeypatch) -> None:
    search = _search_over(monkeypatch)
    query = "mức học phí một tín chỉ"

    results = search.search(query, top_k=len(TEXTS))

    expected = rank_bm25(query, TEXTS, top_k=len(TEXTS))
    assert [(result["chunk_id"], result["score"]) for result in results] == [
        (str(index), pytest.approx(score)) for index, score in expected
    ]
    assert results[0]["bm25_norm_score"] >= 0.25
    assert {result["bm25_index"] for result in results} == {"accented"}
    assert {result["bm25_folded_norm_score"] for result in results} == {None}


def test_partially_unaccented_query_uses_folded_index(monkeypatch) -> None:
    search = _search_over(monkeypatch)
    # Bỏ dấu một phần: "phi", "mot", "tin" chỉ có trong kho ở dạng có dấu.
    query = "học phi mot tin chỉ"

    results = search.search(query, top_k=3)

    assert results[0]["chunk_id"] == TUITION
    assert results[0]["bm25_index"] == "folded"
    assert results[0]["bm25_folded_norm_score"] > results[0]["bm25_norm_score"]


def test_weak_accented_query_stays_on_accented_index(monkeypatch) -> None:
    search = _search_over(monkeypatch)
    # Câu đủ dấu khớp yếu vẫn xếp theo chỉ mục có dấu: không có chữ nào thiếu dấu.
    results = search.search("học phí ký túc xá giá bao nhiêu", top_k=3)

    assert results
    assert results[0]["bm25_norm_score"] < 0.25
    assert {result["bm25_index"] for result in results} == {"accented"}


def test_plain_words_present_in_corpus_do_not_trigger_folded_index(monkeypatch) -> None:
    search = _search_over(monkeypatch)
    # "sinh" và "theo" vốn không dấu và có trong kho; chữ lạ "netflix" không có ở chỉ mục nào.
    results = search.search("sinh theo netflix", top_k=3)

    assert {result["bm25_index"] for result in results} == {"accented"}


def test_folded_path_respects_dataset_filter(monkeypatch) -> None:
    dataset_ids = ["d1"] * len(TEXTS)
    dataset_ids[int(TUITION)] = "d2"
    search = _search_over(monkeypatch, dataset_ids=dataset_ids)

    results = search.search("hoc phi mot tin chi", top_k=3, dataset_ids=["d1"])

    assert TUITION not in {result["chunk_id"] for result in results}
    assert {result["bm25_index"] for result in results} <= {"folded"}


def test_folded_index_rebuilds_after_cache_invalidation(monkeypatch) -> None:
    search = BM25Search()
    chunks = [{"chunk_id": "1", "text": "quy định học phí"}, {"chunk_id": "2", "text": "thư viện"}]
    monkeypatch.setattr(search, "_load_chunks", lambda: chunks)
    assert search.search("ky tuc xa", top_k=1) == []

    chunks.append({"chunk_id": "3", "text": "đăng ký ký túc xá"})
    invalidate_bm25_cache()

    assert search.search("ky tuc xa", top_k=1)[0]["chunk_id"] == "3"


def test_fusion_steps_carry_folded_signal() -> None:
    keyword = [
        {
            "chunk_id": "c1",
            "parent_id": "p1",
            "score": 3.0,
            "bm25_norm_score": 0.1,
            "bm25_folded_norm_score": 0.6,
            "bm25_index": "folded",
        },
        {
            "chunk_id": "c2",
            "parent_id": "p1",
            "score": 2.0,
            "bm25_norm_score": 0.05,
            "bm25_folded_norm_score": 0.4,
            "bm25_index": "folded",
        },
    ]
    vector = [{"chunk_id": "c1", "parent_id": "p1", "score": 0.5}]

    fused = reciprocal_rank_fusion(vector, keyword, top_k=5, vector_weight=0.8)
    by_id = {result["chunk_id"]: result for result in fused}
    assert by_id["c1"]["bm25_folded_norm_score"] == 0.6
    assert by_id["c1"]["bm25_index"] == "folded"

    parents = collapse_parent_results(fused, top_k=5)
    assert len(parents) == 1
    assert parents[0]["bm25_folded_norm_score"] == 0.6

    other_query = [{**parents[0], "score": 0.001, "bm25_folded_norm_score": 0.9}]
    merged = fuse_multi_query_results([parents, other_query], top_k=5)
    assert merged[0]["bm25_folded_norm_score"] == 0.9
    assert merged[0]["bm25_index"] == "folded"


def test_heuristic_rerank_counts_folded_term_coverage_for_unaccented_query(monkeypatch) -> None:
    monkeypatch.setattr(settings, "reranker_vector_weight", 0.0)
    monkeypatch.setattr(settings, "reranker_bm25_weight", 0.0)
    monkeypatch.setattr(settings, "reranker_lexical_weight", 1.0)
    contexts = [
        {"chunk_id": "other", "text": "Lịch học theo tuần.", "vector_score": 0.5, "bm25_score": 1.0},
        {"chunk_id": "tuition", "text": "Mức học phí tín chỉ.", "vector_score": 0.5, "bm25_score": 1.0},
    ]

    results = heuristic_rerank("muc hoc phi tin chi", contexts, top_k=2)

    assert results[0]["chunk_id"] == "tuition"
    assert results[0]["rerank_score"] == pytest.approx(1.0)


def test_retriever_uses_folded_vector_weight_only_for_folded_ranking(monkeypatch) -> None:
    from app.retrieval.retriever import _vector_weight

    monkeypatch.setattr(settings, "hybrid_vector_weight", 0.8)
    monkeypatch.setattr(settings, "hybrid_folded_vector_weight", 0.3)

    assert _vector_weight([{"bm25_index": "folded"}]) == 0.3
    assert _vector_weight([{"bm25_index": "accented"}]) == 0.8
    assert _vector_weight([]) == 0.8

    monkeypatch.setattr(settings, "hybrid_folded_vector_weight", None)
    assert _vector_weight([{"bm25_index": "folded"}]) == 0.8

"""`bm25_norm_score`: điểm BM25 chuẩn hóa về [0, 1] theo cận trên của query (RAG-18)."""

import pytest

from app.retrieval.bm25 import BM25Search, normalize_bm25_score


def _search_over(monkeypatch, texts: list[str]) -> BM25Search:
    search = BM25Search()
    chunks = [{"chunk_id": str(index), "text": text} for index, text in enumerate(texts)]
    monkeypatch.setattr(search, "_load_chunks", lambda: chunks)
    return search


FILLER = [
    "thông tin thư viện mở cửa buổi sáng",
    "lịch học của sinh viên theo tuần",
    "quy định về trang phục khi đến lớp",
    "hướng dẫn đăng nhập hệ thống quản lý",
    "câu lạc bộ âm nhạc tuyển thành viên",
]


def test_normalized_score_stays_in_unit_interval(monkeypatch) -> None:
    search = _search_over(
        monkeypatch,
        FILLER + ["mức học phí tín chỉ học phí học phí", "học phí đóng theo học kỳ"],
    )

    results = search.search("học phí tín chỉ đóng khi nào", top_k=10)

    assert results
    for result in results:
        assert 0.0 <= result["bm25_norm_score"] <= 1.0
        assert result["score"] > 0
    # Thứ hạng vẫn theo điểm thô; điểm chuẩn hóa tỉ lệ thuận với điểm thô trong một query.
    raw = [result["score"] for result in results]
    norm = [result["bm25_norm_score"] for result in results]
    assert raw == sorted(raw, reverse=True)
    assert norm == sorted(norm, reverse=True)


def test_normalized_score_approaches_one_when_every_term_saturates(monkeypatch) -> None:
    saturated = " ".join(["phúc khảo bài thi"] * 400)
    search = _search_over(monkeypatch, FILLER + [saturated])

    top = search.search("phúc khảo bài thi", top_k=1)[0]

    assert top["bm25_norm_score"] == pytest.approx(1.0, abs=0.05)


def test_unseen_query_terms_lower_the_normalized_score(monkeypatch) -> None:
    search = _search_over(monkeypatch, FILLER + ["phúc khảo bài thi kết thúc học phần"])

    known = search.search("phúc khảo bài thi", top_k=1)[0]["bm25_norm_score"]
    # "netflix" không có trong kho: điểm thô không đổi nhưng điểm chuẩn hóa phải giảm.
    with_unseen = search.search("phúc khảo bài thi netflix", top_k=1)[0]

    assert with_unseen["bm25_norm_score"] < known
    assert with_unseen["score"] == pytest.approx(
        search.search("phúc khảo bài thi", top_k=1)[0]["score"]
    )


def test_normalized_score_is_stable_when_corpus_grows(monkeypatch) -> None:
    target = "điều kiện xét học bổng khuyến khích học tập"
    query = "điều kiện học bổng khuyến khích"
    small = _search_over(monkeypatch, FILLER + [target])
    # Kho lớn hơn 8 lần với các tài liệu không liên quan: idf của term query tăng nên
    # điểm thô đổi đáng kể, còn điểm chuẩn hóa gần như giữ nguyên.
    large = _search_over(
        monkeypatch,
        [f"{text} bản {copy}" for copy in range(8) for text in FILLER] + [target],
    )

    small_top = small.search(query, top_k=1)[0]
    large_top = large.search(query, top_k=1)[0]

    raw_change = abs(large_top["score"] - small_top["score"]) / small_top["score"]
    norm_change = abs(large_top["bm25_norm_score"] - small_top["bm25_norm_score"])
    assert raw_change > 0.3
    assert norm_change < 0.1


def test_normalize_bm25_score_clamps_and_handles_empty_bound() -> None:
    assert normalize_bm25_score(5.0, 10.0) == 0.5
    assert normalize_bm25_score(12.0, 10.0) == 1.0
    assert normalize_bm25_score(-1.0, 10.0) == 0.0
    assert normalize_bm25_score(3.0, 0.0) == 0.0

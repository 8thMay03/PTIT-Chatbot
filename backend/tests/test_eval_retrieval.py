"""Unit test cho phần chấm điểm của scripts.eval_retrieval.

Toàn bộ test thuần, không cần mạng, không cần OPENAI_API_KEY, không cần DB:
module chỉ import thư viện chuẩn ở top-level.
"""

import importlib

import pytest

from scripts.eval_retrieval import UNKNOWN_GROUP


def _load_module(monkeypatch: pytest.MonkeyPatch):
    """Nạp lại module trong môi trường không có key để chứng minh không phụ thuộc."""

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    module = importlib.import_module("scripts.eval_retrieval")
    return importlib.reload(module)


def test_module_imports_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module(monkeypatch)
    assert hasattr(module, "compute_metrics")
    assert hasattr(module, "first_hit_rank")


def test_normalize_text_strips_html_and_folds_case() -> None:
    from scripts.eval_retrieval import normalize_text

    assert normalize_text("<b>Học&nbsp;Phí</b>") == "học phí"
    assert normalize_text("  ĐẠI   học\n\nPTIT  ") == "đại học ptit"
    assert normalize_text("") == ""


def test_normalize_text_applies_nfkc_compatibility() -> None:
    from scripts.eval_retrieval import normalize_text

    # ﬁ (U+FB01) là ký tự tương thích, NFKC tách thành "fi".
    assert normalize_text("ﬁle") == "file"
    # Dấu tiếng Việt dạng tổ hợp (a + U+0323) phải về dạng dựng sẵn như trong kho.
    composed = normalize_text("đa\u0323i học")
    assert composed == normalize_text("đại học")
    assert composed == "đại học"


def test_first_hit_rank_matches_any_expected_term_after_normalization() -> None:
    from scripts.eval_retrieval import first_hit_rank

    contexts = [
        {"text": "Thông tin thư viện và thẻ đọc."},
        {"text": "Mức <b>học phí</b> tín chỉ năm 2026."},
        {"text": "Quy chế thi cuối kỳ."},
    ]

    rank, term = first_hit_rank(contexts, ["học phí"])
    assert rank == 2
    assert term == "học phí"

    # Nhiều term: chỉ cần một term xuất hiện là trúng.
    rank, term = first_hit_rank(contexts, ["không có ở đâu", "thẻ đọc"])
    assert rank == 1
    assert term == "thẻ đọc"

    # Term viết hoa vẫn khớp sau casefold.
    rank, _ = first_hit_rank(contexts, ["QUY CHẾ THI"])
    assert rank == 3

    assert first_hit_rank(contexts, ["không tồn tại"]) == (None, None)
    assert first_hit_rank([], ["bất kỳ"]) == (None, None)
    assert first_hit_rank(contexts, ["   "]) == (None, None)


def test_compute_metrics_hits_and_mrr() -> None:
    from scripts.eval_retrieval import compute_metrics

    ranks = [1, None, 4, 10, None, 2]
    metrics = compute_metrics(ranks)
    assert metrics["cases"] == 6
    # Giá trị được làm tròn 6 chữ số thập phân trong báo cáo.
    assert metrics["hit@1"] == pytest.approx(1 / 6, abs=1e-6)
    assert metrics["hit@4"] == pytest.approx(3 / 6, abs=1e-6)
    assert metrics["hit@10"] == pytest.approx(4 / 6, abs=1e-6)
    assert metrics["mrr"] == pytest.approx((1 + 0 + 0.25 + 0.1 + 0 + 0.5) / 6, abs=1e-6)


def test_compute_metrics_empty_and_edge_values() -> None:
    from scripts.eval_retrieval import compute_metrics

    empty = compute_metrics([])
    assert empty["cases"] == 0
    assert empty["mrr"] == 0.0

    all_miss = compute_metrics([None, None])
    assert all_miss["hit@1"] == 0.0
    assert all_miss["mrr"] == 0.0

    first = compute_metrics([1])
    assert first["hit@1"] == 1.0
    assert first["mrr"] == 1.0


def test_diacritics_group_classification() -> None:
    from scripts.eval_retrieval import diacritics_group

    assert diacritics_group("Học phí là bao nhiêu?") == "co_dau"
    assert diacritics_group("cho minh hoi thu tuc nhap hoc?") == "khong_dau"
    assert diacritics_group("tuition fee") == "khong_dau"


def test_case_group_value_defaults_to_unknown() -> None:
    from scripts.eval_retrieval import case_group_value

    assert case_group_value({"question_type": "tuition"}, "question_type") == "tuition"
    assert case_group_value({}, "question_type") == UNKNOWN_GROUP
    assert case_group_value({"source": " "}, "source", "source_document") == UNKNOWN_GROUP


def test_aggregate_metrics_groups_and_overall() -> None:
    from scripts.eval_retrieval import aggregate_metrics

    cases = [
        {
            "id": "a",
            "first_hit_rank": 1,
            "diacritics": "co_dau",
            "question_type": "tuition",
            "source": "so_tay",
        },
        {
            "id": "b",
            "first_hit_rank": None,
            "diacritics": "khong_dau",
            "question_type": "tuition",
            "source": "so_tay",
        },
        {
            "id": "c",
            "first_hit_rank": 2,
            "diacritics": "co_dau",
            "question_type": UNKNOWN_GROUP,
            "source": UNKNOWN_GROUP,
        },
    ]

    metrics = aggregate_metrics(cases)
    assert metrics["overall"]["cases"] == 3
    assert metrics["overall"]["hit@1"] == pytest.approx(1 / 3, abs=1e-6)
    assert metrics["overall"]["mrr"] == pytest.approx((1 + 0 + 0.5) / 3, abs=1e-6)

    assert set(metrics["by_diacritics"]) == {"co_dau", "khong_dau"}
    assert metrics["by_diacritics"]["khong_dau"]["hit@1"] == 0.0
    assert metrics["by_question_type"]["tuition"]["cases"] == 2
    assert metrics["by_source"]["so_tay"]["hit@1"] == pytest.approx(0.5)


def test_collect_metric_rows_flattens_groups_for_compare() -> None:
    from scripts.eval_retrieval import collect_metric_rows

    metrics = {
        "overall": {"cases": 2, "hit@1": 0.5, "hit@4": 1.0, "hit@10": 1.0, "mrr": 0.75},
        "by_diacritics": {
            "co_dau": {"cases": 1, "hit@1": 1.0, "hit@4": 1.0, "hit@10": 1.0, "mrr": 1.0},
        },
    }

    rows = collect_metric_rows(metrics)
    assert rows["overall"]["hit@1"] == 0.5
    assert rows["by_diacritics.co_dau"]["mrr"] == 1.0
    assert set(rows["overall"]) == {"hit@1", "hit@4", "hit@10", "mrr"}


def test_cached_embedding_model_reuses_cache_and_persists(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module(monkeypatch)
    cache_file = tmp_path / "cache.json"

    class FakeInner:
        model_name = "fake-model"

        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def embed(self, texts: list[str]) -> list[list[float]]:
            self.calls.append(list(texts))
            return [[float(len(text)), 1.0] for text in texts]

    inner = FakeInner()
    cached = module.CachedEmbeddingModel(inner, "openai", "fake-model", cache_file)

    first = cached.embed(["aaaa", "bbbbbb"])
    assert first == [[4.0, 1.0], [6.0, 1.0]]
    assert inner.calls == [["aaaa", "bbbbbb"]]
    assert (cached.cache_hits, cached.cache_misses) == (0, 2)
    assert cache_file.exists()

    second_model = module.CachedEmbeddingModel(FakeInner(), "openai", "fake-model", cache_file)
    second = second_model.embed(["bbbbbb", "aaaa", "ccccccc"])
    # Hai câu cũ lấy từ cache, chỉ câu mới gọi API.
    assert second == [[6.0, 1.0], [4.0, 1.0], [7.0, 1.0]]
    assert second_model.inner.calls == [["ccccccc"]]
    assert (second_model.cache_hits, second_model.cache_misses) == (2, 1)

    # Khác model thì khác khóa cache.
    third_model = module.CachedEmbeddingModel(FakeInner(), "openai", "other-model", cache_file)
    third_model.embed(["aaaa"])
    assert third_model.inner.calls == [["aaaa"]]


def test_cache_key_is_model_and_text_sensitive() -> None:
    from scripts.eval_retrieval import CachedEmbeddingModel

    base = CachedEmbeddingModel.cache_key("openai", "m1", "text")
    assert base == CachedEmbeddingModel.cache_key("openai", "m1", "text")
    assert base != CachedEmbeddingModel.cache_key("openai", "m2", "text")
    assert base != CachedEmbeddingModel.cache_key("openai", "m1", "text khác")


def test_load_dataset_requires_question_and_terms(tmp_path) -> None:
    from scripts.eval_retrieval import load_dataset

    good = tmp_path / "good.json"
    good.write_text(
        '[{"id": "q1", "question": "Học phí?", "expected_terms": ["học phí"]}]',
        encoding="utf-8",
    )
    cases = load_dataset(good)
    assert cases == [
        {
            "id": "q1",
            "question": "Học phí?",
            "expected_terms": ["học phí"],
            "source": "unknown",
            "question_type": "unknown",
        }
    ]

    wrapped = tmp_path / "wrapped.json"
    wrapped.write_text(
        '{"cases": [{"id": "q2", "question": "Thi lại?", "expected_terms": ["thi lại"], '
        '"question_type": "exam", "source": "quy_che"}]}',
        encoding="utf-8",
    )
    assert load_dataset(wrapped)[0]["question_type"] == "exam"

    bad = tmp_path / "bad.json"
    bad.write_text('[{"id": "q3", "question": "Thiếu term"}]', encoding="utf-8")
    with pytest.raises(ValueError, match="expected_terms"):
        load_dataset(bad)

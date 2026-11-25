import logging

import pytest

from app.generation import confidence
from app.generation.confidence import (
    GateThresholds,
    assess_context,
    effective_vector_override,
    thresholds_from_settings,
)


def _thresholds(
    bm25_norm: float = 0.25,
    vector: float | None = 0.37,
    rerank: float | None = None,
    vector_source: str = "calibrated",
    folded: float | None = 0.40,
) -> GateThresholds:
    return GateThresholds(
        min_bm25_norm_score=bm25_norm,
        min_vector_score=vector,
        min_rerank_score=rerank,
        embedding_model="text-embedding-3-small",
        vector_source=vector_source,
        rerank_source="calibrated" if rerank is not None else "not_applicable",
        min_bm25_folded_norm_score=folded,
    )


@pytest.fixture
def gate_settings(monkeypatch):
    """Cấu hình gate cố định, độc lập với `.env` của máy chạy test."""
    target = confidence.settings
    monkeypatch.setattr(target, "embedding_model", "text-embedding-3-small")
    monkeypatch.setattr(target, "retrieval_min_vector_score", None)
    monkeypatch.setattr(target, "retrieval_min_bm25_norm_score", 0.25)
    monkeypatch.setattr(target, "retrieval_min_rerank_score", None)
    monkeypatch.setattr(target, "retrieval_min_bm25_folded_norm_score", 0.40)
    monkeypatch.setattr(target, "reranker_enabled", True)
    monkeypatch.setattr(target, "reranker_provider", "heuristic")
    monkeypatch.setattr(target, "reranker_model", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
    monkeypatch.setattr(confidence, "_warned", set())
    return target


def test_passes_when_every_signal_clears_its_threshold() -> None:
    contexts = [
        {"vector_score": 0.62, "bm25_norm_score": 0.41, "rerank_score": 3.2},
        {"vector_score": 0.30, "bm25_norm_score": None, "rerank_score": -4.0},
    ]

    decision = assess_context(contexts, _thresholds(rerank=-1.65))

    assert decision.strong
    assert decision.reason == "passed"
    # Tín hiệu top-1 = max trên các context.
    assert decision.signals == {"vector": 0.62, "bm25_norm": 0.41, "bm25_folded_norm": None, "rerank": 3.2}


@pytest.mark.parametrize(
    ("context", "reason"),
    [
        ({"vector_score": 0.62, "bm25_norm_score": 0.20, "rerank_score": 3.0}, "below_bm25_norm"),
        ({"vector_score": 0.33, "bm25_norm_score": 0.40, "rerank_score": 3.0}, "below_vector"),
        ({"vector_score": 0.62, "bm25_norm_score": 0.40, "rerank_score": -2.0}, "below_rerank"),
    ],
)
def test_fails_when_any_single_signal_is_below_threshold(context: dict, reason: str) -> None:
    decision = assess_context([context], _thresholds(rerank=-1.65))

    assert not decision.strong
    assert decision.reason == reason


def test_missing_signal_counts_as_failure() -> None:
    # Chỉ có kết quả vector (không chunk nào khớp từ khóa): thiếu bm25_norm thì không đạt.
    vector_only = [{"vector_score": 0.9}]
    assert assess_context(vector_only, _thresholds()).reason == "below_bm25_norm"

    # Reranker cross-encoder được bật nhưng context không có rerank_score.
    no_rerank = [{"vector_score": 0.9, "bm25_norm_score": 0.5}]
    assert assess_context(no_rerank, _thresholds(rerank=-1.65)).reason == "below_rerank"


def test_unused_signals_are_ignored() -> None:
    contexts = [{"vector_score": 0.10, "bm25_norm_score": 0.30, "rerank_score": -9.0}]

    decision = assess_context(contexts, _thresholds(vector=None, rerank=None, vector_source="uncalibrated"))

    assert decision.strong
    assert decision.reason == "passed_uncalibrated_model"


def test_folded_signal_passes_keyword_check_without_vector() -> None:
    # Câu gõ thiếu dấu: bm25_norm thấp, chunk đứng đầu nhờ BM25 bỏ dấu không có điểm vector.
    contexts = [
        {"vector_score": None, "bm25_norm_score": 0.05, "bm25_folded_norm_score": 0.52},
        {"vector_score": 0.30, "bm25_norm_score": None, "bm25_folded_norm_score": None},
    ]

    decision = assess_context(contexts, _thresholds())

    assert decision.strong
    assert decision.reason == "passed"
    assert decision.signals["bm25_folded_norm"] == 0.52


def test_folded_signal_below_threshold_fails_on_bm25_norm() -> None:
    contexts = [{"vector_score": 0.6, "bm25_norm_score": 0.05, "bm25_folded_norm_score": 0.39}]

    decision = assess_context(contexts, _thresholds())

    assert not decision.strong
    assert decision.reason == "below_bm25_norm"


def test_folded_signal_ignored_when_threshold_disabled() -> None:
    contexts = [{"vector_score": 0.6, "bm25_norm_score": 0.05, "bm25_folded_norm_score": 0.9}]

    assert assess_context(contexts, _thresholds(folded=None)).reason == "below_bm25_norm"


def test_folded_path_still_checks_rerank() -> None:
    contexts = [{"bm25_norm_score": 0.05, "bm25_folded_norm_score": 0.6, "rerank_score": -3.0}]

    decision = assess_context(contexts, _thresholds(rerank=-1.65))

    assert not decision.strong
    assert decision.reason == "below_rerank"


def test_folded_threshold_comes_from_settings(gate_settings) -> None:
    assert thresholds_from_settings().min_bm25_folded_norm_score == 0.40

    gate_settings.retrieval_min_bm25_folded_norm_score = None
    assert thresholds_from_settings().min_bm25_folded_norm_score is None


def test_empty_context_is_weak() -> None:
    decision = assess_context([], _thresholds())

    assert not decision.strong
    assert decision.reason == "no_context"
    assert decision.signals == {"vector": None, "bm25_norm": None, "bm25_folded_norm": None, "rerank": None}


def test_thresholds_use_calibrated_table_for_known_model(gate_settings) -> None:
    thresholds = thresholds_from_settings()

    assert thresholds.min_vector_score == confidence.VECTOR_THRESHOLDS["text-embedding-3-small"]
    assert thresholds.vector_source == "calibrated"
    assert thresholds.min_bm25_norm_score == 0.25
    # Reranker heuristic cho điểm tương đối: không bao giờ dùng làm ngưỡng.
    assert thresholds.min_rerank_score is None
    assert thresholds.rerank_source == "not_applicable"


def test_explicit_vector_threshold_overrides_table(gate_settings) -> None:
    gate_settings.retrieval_min_vector_score = 0.5

    thresholds = thresholds_from_settings()

    assert thresholds.min_vector_score == 0.5
    assert thresholds.vector_source == "override"


def test_legacy_default_vector_threshold_does_not_override_table(gate_settings) -> None:
    # `.env` cũ và runtime config đã lưu còn 0.30: không được đè bảng đã hiệu chỉnh.
    gate_settings.retrieval_min_vector_score = 0.30

    assert effective_vector_override(0.30) is None
    assert thresholds_from_settings().vector_source == "calibrated"


def test_uncalibrated_model_drops_vector_signal_and_warns_once(gate_settings, caplog) -> None:
    gate_settings.embedding_model = "bge-m3"

    with caplog.at_level(logging.WARNING, logger="app.generation.confidence"):
        first = thresholds_from_settings()
        thresholds_from_settings()

    assert first.min_vector_score is None
    assert first.vector_source == "uncalibrated"
    warnings = [record for record in caplog.records if "bge-m3" in record.getMessage()]
    assert len(warnings) == 1


def test_cross_encoder_uses_rerank_threshold_only_when_calibrated(gate_settings, caplog) -> None:
    gate_settings.reranker_provider = "cross-encoder"
    calibrated = thresholds_from_settings()
    assert calibrated.min_rerank_score == confidence.RERANK_THRESHOLDS[gate_settings.reranker_model]
    assert calibrated.rerank_source == "calibrated"

    gate_settings.reranker_model = "BAAI/bge-reranker-v2-m3"
    with caplog.at_level(logging.WARNING, logger="app.generation.confidence"):
        uncalibrated = thresholds_from_settings()
    assert uncalibrated.min_rerank_score is None
    assert uncalibrated.rerank_source == "uncalibrated"
    assert any("bge-reranker" in record.getMessage() for record in caplog.records)

    gate_settings.retrieval_min_rerank_score = 0.5
    assert thresholds_from_settings().min_rerank_score == 0.5

    gate_settings.reranker_enabled = False
    assert thresholds_from_settings().rerank_source == "not_applicable"


@pytest.mark.parametrize("provider", ["rerank_api", "cohere", "jina", "voyage", "pinecone", "tei"])
def test_rerank_api_uses_override_only_never_cross_encoder_table(gate_settings, caplog, provider) -> None:
    # Trùng tên mô hình trong RERANK_THRESHOLDS vẫn không dùng: điểm API khác thang đo (D-03).
    gate_settings.reranker_provider = provider
    with caplog.at_level(logging.WARNING, logger="app.generation.confidence"):
        uncalibrated = thresholds_from_settings()
    assert uncalibrated.min_rerank_score is None
    assert uncalibrated.rerank_source == "uncalibrated"
    assert any("chưa có ngưỡng hiệu chỉnh" in record.getMessage() for record in caplog.records)
    # BM25/vector vẫn kiểm tra; điểm rerank bất kỳ không làm gate trượt.
    assert uncalibrated.min_vector_score is not None
    contexts = [{"vector_score": 0.6, "bm25_norm_score": 0.4, "rerank_score": -100.0}]
    assert assess_context(contexts, uncalibrated).strong

    gate_settings.retrieval_min_rerank_score = 0.3
    override = thresholds_from_settings()
    assert override.min_rerank_score == 0.3
    assert override.rerank_source == "override"
    weak = [{"vector_score": 0.6, "bm25_norm_score": 0.4, "rerank_score": 0.1}]
    assert assess_context(weak, override).reason == "below_rerank"


def test_raw_bm25_threshold_no_longer_affects_gate(gate_settings) -> None:
    # Giá trị BM25 thô đã lưu (2.0 hay cao bất thường) không được làm gate từ chối mọi câu.
    gate_settings.retrieval_min_bm25_score = 1000.0
    contexts = [{"vector_score": 0.6, "bm25_score": 3.0, "bm25_norm_score": 0.4}]

    assert assess_context(contexts, thresholds_from_settings()).strong

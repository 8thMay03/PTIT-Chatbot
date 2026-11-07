"""Confidence gate: quyết định context truy xuất có đủ mạnh để gọi LLM hay không (RAG-18).

Gate đạt khi **mọi** tín hiệu đã hiệu chỉnh đều vượt ngưỡng; tín hiệu top-1 là max
trên các context sau rerank:

- ``bm25_norm`` (BM25 chuẩn hóa [0, 1], không phụ thuộc kích thước kho): luôn dùng.
- ``vector`` (cosine): thang đo khác nhau giữa các embedding model nên ngưỡng gắn với
  tên model (``VECTOR_THRESHOLDS``). Model chưa hiệu chỉnh và không có ghi đè thì bỏ
  tín hiệu này, kèm cảnh báo, thay vì âm thầm dùng ngưỡng của model khác.
- ``rerank``: chỉ khi reranker là ``cross-encoder`` (điểm tuyệt đối). Reranker
  ``heuristic`` chuẩn hóa min-max trong danh sách ứng viên nên top-1 luôn cao, không
  dùng làm ngưỡng được.

Ngưỡng chọn từ phân bố điểm đo trên ``ptit_rag_300``/``ptit_ragas_100`` và bộ câu không
có đáp án ``ptit_no_answer_56`` — xem ``documents/rag-eval/rag-18/``. Kho đổi nhiều thì
đo lại bằng ``python -m scripts.eval_confidence --sweep``.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cosine tối thiểu theo embedding model (RAG-18, đo 2026-11-08 trên Sổ tay D26). Đây là sàn an
# toàn: thấp hơn mọi câu có đáp án đã đo (min 0.385), phần phân tách chính do bm25_norm/rerank.
VECTOR_THRESHOLDS: dict[str, float] = {
    "text-embedding-3-small": 0.37,
}
# Điểm cross-encoder tối thiểu theo model reranker (logit, không phải xác suất).
RERANK_THRESHOLDS: dict[str, float] = {
    "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1": -1.65,
}
# Giá trị mặc định cũ của RETRIEVAL_MIN_VECTOR_SCORE, chưa từng hiệu chỉnh và còn nằm
# trong nhiều `.env`/runtime config đã lưu: coi như chưa đặt để bảng theo model có hiệu lực.
LEGACY_DEFAULT_MIN_VECTOR_SCORE = 0.30

_warned: set[str] = set()


@dataclass(frozen=True)
class GateThresholds:
    """Ngưỡng hiệu lực; ``None`` nghĩa là không dùng tín hiệu đó."""

    min_bm25_norm_score: float
    min_vector_score: float | None
    min_rerank_score: float | None
    embedding_model: str
    vector_source: str  # calibrated | override | uncalibrated
    rerank_source: str  # calibrated | override | uncalibrated | not_applicable

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ConfidenceDecision:
    strong: bool
    reason: str
    signals: dict[str, float | None]


def effective_vector_override(value: float | None) -> float | None:
    """Ghi đè ngưỡng vector do người dùng đặt, bỏ qua giá trị mặc định cũ 0.30."""
    if value is None or abs(float(value) - LEGACY_DEFAULT_MIN_VECTOR_SCORE) < 1e-9:
        return None
    return float(value)


def thresholds_from_settings() -> GateThresholds:
    """Ngưỡng theo cấu hình hiện tại (env, runtime config) và bảng hiệu chỉnh theo model."""
    model = settings.embedding_model
    override = effective_vector_override(settings.retrieval_min_vector_score)
    if override is not None:
        min_vector, vector_source = override, "override"
    elif model in VECTOR_THRESHOLDS:
        min_vector, vector_source = VECTOR_THRESHOLDS[model], "calibrated"
    else:
        min_vector, vector_source = None, "uncalibrated"
        _warn_once(
            f"vector:{model}",
            "Embedding model %r chưa có ngưỡng cosine hiệu chỉnh: confidence gate bỏ tín hiệu "
            "vector. Đặt RETRIEVAL_MIN_VECTOR_SCORE hoặc chạy scripts.eval_confidence để hiệu chỉnh.",
            model,
        )

    min_rerank: float | None = None
    rerank_source = "not_applicable"
    if settings.reranker_enabled and settings.reranker_provider == "cross-encoder":
        if settings.retrieval_min_rerank_score is not None:
            min_rerank, rerank_source = float(settings.retrieval_min_rerank_score), "override"
        elif settings.reranker_model in RERANK_THRESHOLDS:
            min_rerank, rerank_source = RERANK_THRESHOLDS[settings.reranker_model], "calibrated"
        else:
            rerank_source = "uncalibrated"
            _warn_once(
                f"rerank:{settings.reranker_model}",
                "Reranker %r chưa có ngưỡng hiệu chỉnh: confidence gate bỏ tín hiệu rerank. "
                "Đặt RETRIEVAL_MIN_RERANK_SCORE hoặc chạy scripts.eval_confidence để hiệu chỉnh.",
                settings.reranker_model,
            )

    return GateThresholds(
        min_bm25_norm_score=float(settings.retrieval_min_bm25_norm_score),
        min_vector_score=min_vector,
        min_rerank_score=min_rerank,
        embedding_model=model,
        vector_source=vector_source,
        rerank_source=rerank_source,
    )


def assess_context(contexts: list[dict], thresholds: GateThresholds) -> ConfidenceDecision:
    """Gate đạt khi mọi tín hiệu đang dùng đều vượt ngưỡng; thiếu tín hiệu tính là không đạt.

    ``reason`` khi không đạt nêu tín hiệu đầu tiên trượt (``no_context``,
    ``below_bm25_norm``, ``below_vector``, ``below_rerank``); khi đạt là ``passed`` hoặc
    ``passed_uncalibrated_model`` nếu đã phải bỏ tín hiệu vector.
    """
    signals = {
        "vector": _top(contexts, "vector_score"),
        "bm25_norm": _top(contexts, "bm25_norm_score"),
        "rerank": _top(contexts, "rerank_score"),
    }
    if not contexts:
        return ConfidenceDecision(False, "no_context", signals)

    checks = (
        ("bm25_norm", thresholds.min_bm25_norm_score),
        ("vector", thresholds.min_vector_score),
        ("rerank", thresholds.min_rerank_score),
    )
    for name, minimum in checks:
        if minimum is None:
            continue
        value = signals[name]
        if value is None or value < minimum:
            return ConfidenceDecision(False, f"below_{name}", signals)

    reason = "passed_uncalibrated_model" if thresholds.vector_source == "uncalibrated" else "passed"
    return ConfidenceDecision(True, reason, signals)


def _top(contexts: list[dict], field: str) -> float | None:
    values = [float(context[field]) for context in contexts if context.get(field) is not None]
    return max(values) if values else None


def _warn_once(key: str, message: str, *args: object) -> None:
    if key in _warned:
        return
    _warned.add(key)
    logger.warning(message, *args)

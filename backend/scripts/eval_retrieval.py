"""Đánh giá retrieval offline: hit@k, MRR trên bộ câu hỏi có bằng chứng (schema v1 hoặc v2).

Chỉ chạy phần truy xuất, không sinh câu trả lời và không gọi LLM judge. Các chế độ:

- ``bm25``: tìm từ khóa BM25 trên chunk con, gộp về chunk cha.
- ``vector``: tìm pgvector, gộp về chunk cha.
- ``hybrid``: đúng pipeline `Retriever.retrieve` (RRF vector + BM25, gộp cha).
- ``full``: hybrid + multi-query + rerank theo cấu hình hiện tại (bỏ guardrail scope
  và lọc strong_context vì không thuộc về retrieval).

Chỉ số:

- hit@1/4/10 + MRR theo rank context đầu tiên thỏa một nhóm bằng chứng.
- coverage@1/4/10: tỉ lệ nhóm bằng chứng được phủ bởi top-k context (recall theo
  nhóm) — đo việc truy xuất đủ mọi thông tin cần cho câu trả lời, không chỉ một.
- all_groups@1/4/10: tỉ lệ câu có top-k phủ đủ **mọi** nhóm — chỉ số chính cho câu
  multi-hop/so sánh (từ báo cáo schema v4).
- section_dominance: tỉ lệ câu có mỗi section (source + section_path) trong top-4 —
  phát hiện section quá lớn chiếm chỗ đáp án đúng.

Dataset nạp qua ``scripts.eval_dataset`` (đặc tả: documents/rag-eval/dataset-schema-v2.md).
File v1: mỗi `expected_terms` là một nhóm, nên câu trúng khi một term xuất hiện trong
text của context sau khi chuẩn hóa NFKC + bỏ thẻ HTML + casefold — như trước. Câu không
có bằng chứng (không có đáp án, câu global chỉ chấm bằng claim) bị bỏ qua và ghi vào
``dataset.skipped_no_evidence``. Nhãn không phụ thuộc chunk ID nên dùng được khi thay
đổi chunking. Embedding câu hỏi được cache theo khóa
(provider, model, text) để chạy lại không tốn API.

Ví dụ::

    python -m scripts.eval_retrieval --mode hybrid
    python -m scripts.eval_retrieval --mode full --output documents/rag-eval/full.json
    python -m scripts.eval_retrieval --compare a.json b.json
    python -m scripts.eval_retrieval --mode full --perturb typo --seed 20261121

``--perturb strip_all|strip_partial|typo`` đo trên biến thể câu hỏi sinh lúc chạy
(``scripts.typo_variants``, seed cố định) mà không ghi fixture mới. ``--split dev|test``
chỉ chạy các câu v2 thuộc split đó.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any, Callable

from scripts.eval_dataset import (
    SPLITS,
    UNKNOWN,
    Dataset,
    all_groups_rank,
    first_hit,
    group_ranks,
    groups_from_terms,
    load_cases,
    normalize_text,  # noqa: F401 — giữ API cũ, các test vẫn import normalize_text từ module này
)
from scripts.eval_dataset import coverage_by_k as group_coverage_by_k

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_DATASET = BACKEND_DIR / "tests" / "fixtures" / "ptit_ragas_100.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "documents" / "rag-eval"
DEFAULT_CACHE_FILE = BACKEND_DIR / "storage" / "eval" / "embedding_cache.json"
MODES = ("bm25", "vector", "hybrid", "full")
METRIC_KS = (1, 4, 10)
# v3: thêm `retrieved[].section_path` và `metrics.section_dominance`.
# v4: thêm `cases[].split`, `cases[].evidence_groups`, `cases[].all_groups_rank` và
# metric `all_groups@k`; `dataset` ghi schema/tên/split của dataset và câu bị bỏ qua.
SCHEMA_VERSION = 4
DOMINANCE_K = 4
DEFAULT_PERTURB_SEED = 20261121
RANK_METRICS = ("hit@1", "hit@4", "hit@10", "mrr")
COVERAGE_METRICS = ("coverage@1", "coverage@4", "coverage@10")
ALL_GROUPS_METRICS = ("all_groups@1", "all_groups@4", "all_groups@10")
REPORT_METRICS = RANK_METRICS + COVERAGE_METRICS + ALL_GROUPS_METRICS

VIETNAMESE_DIACRITICS = set(
    "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộ"
    "ơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
)
UNKNOWN_GROUP = UNKNOWN

CONFIG_FIELDS = (
    "chunk_size",
    "chunk_overlap",
    "parent_child_chunking_enabled",
    "child_chunk_size",
    "child_chunk_overlap",
    "min_child_chunk_chars",
    "hybrid_vector_weight",
    "hybrid_candidate_multiplier",
    "hybrid_rrf_k",
    "retrieval_min_vector_score",
    "retrieval_min_bm25_score",
    "query_rewrite_use_llm",
    "query_correction_enabled",
    "multi_query_enabled",
    "multi_query_use_llm",
    "multi_query_count",
    "reranker_enabled",
    "reranker_provider",
    "reranker_model",
    "reranker_candidate_multiplier",
    "reranker_vector_weight",
    "reranker_bm25_weight",
    "reranker_lexical_weight",
    "retrieval_default_top_k",
)


# ---------------------------------------------------------------------------
# Phần chấm điểm thuần (không cần DB/mạng, dùng cho unit test)
# ---------------------------------------------------------------------------


def first_hit_rank(
    contexts: list[dict],
    expected_terms: list[str],
    text_field: str = "text",
) -> tuple[int | None, str | None]:
    """Tìm rank context đầu tiên chứa một term kỳ vọng (mỗi term là một nhóm bằng chứng).

    Trả về ``(rank_bắt_đầu_từ_1, term_gốc)``; ``(None, None)`` nếu không trúng.
    """

    return first_hit(group_ranks(contexts, groups_from_terms(expected_terms), text_field))


def compute_metrics(ranks: list[int | None], ks: tuple[int, ...] = METRIC_KS) -> dict:
    """Tính hit@k và MRR từ danh sách rank trúng đầu tiên (None = trượt)."""

    total = len(ranks)
    if total == 0:
        return {"cases": 0, **{f"hit@{k}": 0.0 for k in ks}, "mrr": 0.0}
    metrics = {"cases": total}
    for k in ks:
        hits = sum(1 for rank in ranks if rank is not None and rank <= k)
        metrics[f"hit@{k}"] = round(hits / total, 6)
    reciprocal = [1.0 / rank if rank is not None else 0.0 for rank in ranks]
    metrics["mrr"] = round(fmean(reciprocal), 6)
    return metrics


def compute_all_groups_metrics(ranks: list[int | None], ks: tuple[int, ...] = METRIC_KS) -> dict:
    """all_groups@k: tỉ lệ câu có top-k phủ đủ mọi nhóm bằng chứng (rank = all_groups_rank)."""

    total = len(ranks)
    if total == 0:
        return {f"all_groups@{k}": 0.0 for k in ks}
    return {
        f"all_groups@{k}": round(sum(1 for rank in ranks if rank is not None and rank <= k) / total, 6)
        for k in ks
    }


def coverage_by_k(
    contexts: list[dict],
    expected_terms: list[str],
    ks: tuple[int, ...] = METRIC_KS,
    text_field: str = "text",
) -> dict[str, float]:
    """Tỉ lệ `expected_terms` được phủ bởi top-k context, cho từng k.

    coverage@k = số term xuất hiện trong ít nhất một context của top-k /
    tổng số term. Đây là recall theo term: câu hỏi cần nhiều thông tin thì
    đòi hỏi phủ đủ mọi term, không chỉ trúng một.
    """

    return group_coverage_by_k(group_ranks(contexts, groups_from_terms(expected_terms), text_field), ks)


def compute_coverage_metrics(
    coverages: list[dict[str, float]],
    ks: tuple[int, ...] = METRIC_KS,
) -> dict:
    """Trung bình coverage@k trên các câu; câu thiếu dữ liệu coverage bị bỏ qua."""

    metrics: dict[str, float] = {}
    for k in ks:
        name = f"coverage@{k}"
        values = [coverage[name] for coverage in coverages if name in coverage]
        metrics[name] = round(fmean(values), 6) if values else 0.0
    return metrics


def diacritics_group(question: str) -> str:
    """Phân loại câu hỏi có dấu / không dấu tiếng Việt."""

    folded = question.casefold()
    return "co_dau" if any(char in VIETNAMESE_DIACRITICS for char in folded) else "khong_dau"


def aggregate_metrics(case_results: list[dict]) -> dict:
    """Gộp chỉ số tổng và theo nhóm nguồn / loại câu hỏi / dấu."""

    def summarize(items: list[dict]) -> dict:
        metrics = compute_metrics([item["first_hit_rank"] for item in items])
        metrics.update(
            compute_coverage_metrics([item.get("coverage") or {} for item in items])
        )
        if items and all("all_groups_rank" in item for item in items):
            metrics.update(compute_all_groups_metrics([item["all_groups_rank"] for item in items]))
        return metrics

    grouped: dict[str, dict[str, dict]] = {}
    for section, key_fn in (
        ("by_diacritics", lambda item: item["diacritics"]),
        ("by_question_type", lambda item: item["question_type"]),
        ("by_source", lambda item: item["source"]),
    ):
        buckets: dict[str, list[dict]] = {}
        for item in case_results:
            buckets.setdefault(key_fn(item), []).append(item)
        grouped[section] = {label: summarize(items) for label, items in sorted(buckets.items())}

    return {
        "overall": summarize(case_results),
        **grouped,
        "section_dominance": section_dominance(case_results),
    }


def section_dominance(case_results: list[dict], k: int = DOMINANCE_K, limit: int = 10) -> dict:
    """Tỉ lệ câu hỏi có mỗi section trong top-k, section chiếm chỗ nhiều nhất trước.

    Một section quá lớn (nuốt nhiều Điều) xuất hiện trong top-k của rất nhiều câu và
    đẩy đáp án đúng ra ngoài. Section = ``source_name`` + ``section_path``; báo cáo cũ
    chưa có ``section_path`` thì dùng ``heading``.
    """

    total = len(case_results)
    counts: dict[str, int] = {}
    for item in case_results:
        sections = {
            section_key(context)
            for context in item.get("retrieved") or []
            if int(context.get("rank") or 0) <= k
        }
        for section in sections:
            counts[section] = counts.get(section, 0) + 1
    ranked = sorted(counts.items(), key=lambda entry: (-entry[1], entry[0]))
    top = [
        {"section": section, "cases": count, "share": round(count / total, 6)}
        for section, count in ranked[:limit]
    ]
    return {"k": k, "max_share": top[0]["share"] if top else 0.0, "top": top}


def section_key(context: dict) -> str:
    section = str(context.get("section_path") or context.get("heading") or "").strip() or "(không tiêu đề)"
    source = str(context.get("source_name") or "").strip()
    return f"{source} :: {section}" if source else section


# ---------------------------------------------------------------------------
# Hạ tầng đánh giá: cache embedding, fingerprint, git, dataset
# ---------------------------------------------------------------------------


class CachedEmbeddingModel:
    """Bọc embedding model của app, cache vector theo khóa (provider, model, text)."""

    def __init__(self, inner: Any, provider: str, model: str, cache_file: Path) -> None:
        self.inner = inner
        self.provider = provider
        self.model = model
        self.cache_file = cache_file
        self.cache_hits = 0
        self.cache_misses = 0
        self._cache: dict[str, list[float]] = {}
        if cache_file.exists():
            try:
                payload = json.loads(cache_file.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    self._cache = payload
            except (OSError, json.JSONDecodeError) as exc:
                print(f"Cảnh báo: bỏ qua cache hỏng {cache_file}: {exc}", file=sys.stderr)

    @staticmethod
    def cache_key(provider: str, model: str, text: str, query: bool = False) -> str:
        # Mô hình nhúng câu hỏi khác đoạn tài liệu: tách khoá cache của câu hỏi. Mô hình
        # không phân biệt giữ khoá cũ để cache đã có vẫn dùng được.
        marker = "\x00query" if query else ""
        material = f"{provider}\x00{model}\x00{text}{marker}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, query=False)

    def embed_query(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, query=True)

    def _embed(self, texts: list[str], *, query: bool) -> list[list[float]]:
        if not texts:
            return []
        query = query and bool(getattr(self.inner, "distinguishes_queries", False))
        results: list[list[float] | None] = [None] * len(texts)
        missing: list[tuple[int, str, str]] = []
        for index, text in enumerate(texts):
            key = self.cache_key(self.provider, self.model, text, query)
            cached = self._cache.get(key)
            if cached is not None:
                results[index] = cached
                self.cache_hits += 1
            else:
                missing.append((index, key, text))

        if missing:
            inner_embed = getattr(self.inner, "embed_query", self.inner.embed) if query else self.inner.embed
            vectors = inner_embed([text for _, _, text in missing])
            if len(vectors) != len(missing):
                raise RuntimeError(
                    f"Embedding model trả về {len(vectors)} vector cho {len(missing)} văn bản"
                )
            for (index, key, _), vector in zip(missing, vectors):
                self._cache[key] = [float(value) for value in vector]
                results[index] = self._cache[key]
                self.cache_misses += 1
            self._save()

        return [vector for vector in results if vector is not None]

    def _save(self) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.cache_file.with_suffix(".tmp")
        temp_file.write_text(
            json.dumps(self._cache, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_file.replace(self.cache_file)


def snapshot_corpus() -> dict:
    """Fingerprint kho tài liệu: hash các content_hash của document + số chunk."""

    from sqlalchemy import func, select

    from app.db.models import Chunk, Document
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        rows = session.execute(select(Document.id, Document.content_hash).order_by(Document.id)).all()
        chunk_count = session.scalar(select(func.count()).select_from(Chunk))
        embedded_count = session.scalar(
            select(func.count()).select_from(Chunk).where(Chunk.embedding.is_not(None))
        )

    material = "\n".join(f"{document_id}:{content_hash}" for document_id, content_hash in rows)
    material += f"|chunks={chunk_count}|embedded={embedded_count}"
    return {
        "fingerprint": hashlib.sha256(material.encode("utf-8")).hexdigest(),
        "documents": len(rows),
        "chunks": int(chunk_count or 0),
        "embedded_chunks": int(embedded_count or 0),
        "method": "sha256(sorted document content_hash + chunk counts)",
    }


def snapshot_config() -> dict:
    from app.core.config import settings

    return {field: getattr(settings, field) for field in CONFIG_FIELDS}


def git_info() -> dict:
    def run(*arguments: str) -> str:
        try:
            completed = subprocess.run(
                ["git", *arguments],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
        except OSError:
            return ""
        return completed.stdout.strip() if completed.returncode == 0 else ""

    commit = run("rev-parse", "HEAD") or None
    branch = run("rev-parse", "--abbrev-ref", "HEAD") or None
    status_lines = run("status", "--porcelain=v1").splitlines()
    dirty = any(not line.startswith("??") for line in status_lines)
    return {"commit": commit, "branch": branch, "dirty": dirty}


def load_dataset(path: Path, split: str | None = None) -> list[dict]:
    """Nạp dataset v1/v2 (``scripts.eval_dataset``), chỉ giữ câu có bằng chứng."""

    return select_cases(load_cases(path), split)[0]


def select_cases(dataset: Dataset, split: str | None = None) -> tuple[list[dict], list[str]]:
    """Câu dùng để đo retrieval và id các câu bị bỏ vì không có bằng chứng.

    v1: mỗi `expected_terms` là một nhóm bằng chứng (trúng khi một term xuất hiện).
    """

    cases: list[dict] = []
    skipped: list[str] = []
    for case in dataset.cases:
        if split and case.split != split:
            continue
        if not case.evidence:
            skipped.append(case.id)
            continue
        cases.append(
            {
                "id": case.id,
                "question": case.query,
                "evidence": case.evidence,
                "source": case.source,
                "question_type": case.query_type,
                "split": case.split,
            }
        )
    if not cases:
        scope = f" thuộc split {split!r}" if split else ""
        raise ValueError(f"{dataset.origin} không có câu nào{scope} có bằng chứng để đo retrieval")
    return cases, skipped


def dataset_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Xây pipeline retrieval theo chế độ
# ---------------------------------------------------------------------------


def uses_llm_queries() -> bool:
    """Bước tạo truy vấn có gọi LLM (sửa câu, rewrite, multi-query) nên không đoán trước được."""

    from app.core.config import settings

    return (
        settings.query_correction_enabled
        or settings.query_rewrite_use_llm
        or (settings.multi_query_enabled and settings.multi_query_use_llm)
    )


def correction_trace(correction: Any, elapsed_ms: float) -> dict:
    """Ghi vết bước sửa câu cho báo cáo (``QueryCorrectionResult`` + thời gian)."""

    return {
        "corrected": correction.corrected,
        "reason": correction.reason,
        "text": correction.text,
        "llm_output": correction.llm_output,
        "elapsed_ms": round(elapsed_ms, 1),
    }


def build_retrieval_fn(
    mode: str,
    top_k: int,
    embedding_model: Any | None,
    trace: dict | None = None,
) -> Callable[[str], list[dict]]:
    """Dựng hàm retrieval dùng đúng component của app cho từng chế độ.

    ``trace``: chế độ full ghi kết quả bước sửa câu của lần gọi gần nhất vào
    ``trace["correction"]`` (xem :func:`correction_trace`).
    """

    from app.core.config import settings
    from app.retrieval.bm25 import BM25Search
    from app.retrieval.parent_child import collapse_parent_results
    from app.retrieval.retriever import Retriever
    from app.vectordb import create_vector_store

    keyword_search = BM25Search()
    vector_store = create_vector_store()
    candidate_count = max(top_k, top_k * settings.hybrid_candidate_multiplier)

    if mode == "bm25":
        return lambda query: collapse_parent_results(
            keyword_search.search(query, top_k=candidate_count), top_k=top_k
        )

    if mode == "vector":
        if embedding_model is None:
            raise ValueError("Chế độ vector cần embedding model")

        def retrieve_vector(query: str) -> list[dict]:
            query_embedding = embedding_model.embed_query([query])[0]
            return collapse_parent_results(
                vector_store.search(query_embedding, top_k=candidate_count), top_k=top_k
            )

        return retrieve_vector

    if mode == "hybrid":
        if embedding_model is None:
            raise ValueError("Chế độ hybrid cần embedding model")
        retriever = Retriever(
            embedding_model=embedding_model,
            vector_store=vector_store,
            keyword_search=keyword_search,
        )
        return lambda query: retriever.retrieve(query, top_k=top_k)

    # mode == "full": tái dựng RagChain.retrieve_context nhưng bỏ guardrail scope
    # (không thuộc retrieval) và bỏ lọc strong_context (chỉ dùng khi chốt câu trả lời).
    from app.generation.multi_query import VietnameseMultiQueryGenerator
    from app.generation.query_rewriter import VietnameseQueryRewriter
    from app.guardrails import contains_prompt_injection
    from app.retrieval.multi_query import fuse_multi_query_results
    from app.retrieval.reranker import Reranker

    if embedding_model is None:
        raise ValueError("Chế độ full cần embedding model")
    retriever = Retriever(
        embedding_model=embedding_model,
        vector_store=vector_store,
        keyword_search=keyword_search,
    )
    rewriter = VietnameseQueryRewriter()
    multi_query_generator = VietnameseMultiQueryGenerator()
    reranker = Reranker() if settings.reranker_enabled else None
    if uses_llm_queries():
        print(
            "Cảnh báo: sửa câu/query rewrite/multi-query dùng LLM nên kết quả có thể không lặp lại được.",
            file=sys.stderr,
        )

    def retrieve_full(query: str) -> list[dict]:
        started = time.perf_counter()
        correction = rewriter.correct(query)
        if trace is not None:
            trace["correction"] = correction_trace(correction, (time.perf_counter() - started) * 1000)
        rewritten = rewriter.rewrite(query, history=None, correction=correction)
        queries = multi_query_generator.generate(rewritten)
        candidate_count_full = (
            max(top_k, top_k * settings.reranker_candidate_multiplier)
            if settings.reranker_enabled
            else top_k
        )
        result_sets = [retriever.retrieve(item, top_k=candidate_count_full) for item in queries]
        contexts = fuse_multi_query_results(result_sets, top_k=candidate_count_full)
        contexts = [
            context
            for context in contexts
            if not contains_prompt_injection(str(context.get("text", "")))
        ]
        if reranker is not None:
            contexts = reranker.rerank(rewritten, contexts, top_k=top_k)
        else:
            contexts = contexts[:top_k]
        return contexts

    return retrieve_full


def warm_cache_texts(mode: str, questions: list[str]) -> list[str]:
    """Liệt kê trước các câu sẽ cần embed để gọi API theo lô thay vì từng câu.

    Với chế độ full dùng LLM cho sửa câu/rewrite/multi-query thì không đoán trước được,
    trả rỗng và để cache hoạt động per-call (không gọi LLM chỉ để làm ấm cache).
    """

    if mode in ("bm25",):
        return []
    if mode in ("vector", "hybrid"):
        return list(questions)

    if uses_llm_queries():
        return []
    from app.generation.multi_query import VietnameseMultiQueryGenerator
    from app.generation.query_rewriter import VietnameseQueryRewriter

    rewriter = VietnameseQueryRewriter()
    generator = VietnameseMultiQueryGenerator()
    texts: list[str] = []
    for question in questions:
        rewritten = rewriter.rewrite(question, history=None)
        texts.extend(generator.generate(rewritten))
    return texts


# ---------------------------------------------------------------------------
# Chạy đánh giá
# ---------------------------------------------------------------------------


def run_case(question: str, retrieval_fn: Callable[[str], list[dict]], evidence: tuple) -> dict:
    contexts = retrieval_fn(question)
    ranks = group_ranks(contexts, evidence)
    rank, matched_term = first_hit(ranks)
    retrieved = []
    for position, context in enumerate(contexts[: max(METRIC_KS)], start=1):
        retrieved.append(
            {
                "rank": position,
                "chunk_id": str(context.get("chunk_id") or ""),
                "source_name": str(context.get("source_name") or ""),
                "heading": str(context.get("heading") or ""),
                "section_path": str(context.get("section_path") or ""),
                "score": round(float(context.get("score") or 0.0), 6),
            }
        )
    return {
        "first_hit_rank": rank,
        "matched_term": matched_term,
        "retrieved": retrieved,
        "coverage": group_coverage_by_k(ranks, METRIC_KS),
        "all_groups_rank": all_groups_rank(ranks),
    }


def evaluate(mode: str, cases: list[dict], top_k: int, cache_file: Path) -> dict:
    from app.core.config import settings

    started = time.monotonic()
    embedding_block = {"provider": None, "model": None, "cache_file": str(cache_file), "cache_hits": 0, "cache_misses": 0}
    embedding_model = None
    if mode in ("vector", "hybrid", "full"):
        from app.embeddings import create_embedding_model

        inner = create_embedding_model()
        model_name = str(getattr(inner, "model_name", "") or settings.embedding_model)
        embedding_model = CachedEmbeddingModel(inner, settings.embedding_provider, model_name, cache_file)
        warm_texts = warm_cache_texts(mode, [case["question"] for case in cases])
        if warm_texts:
            embedding_model.embed_query(warm_texts)
        embedding_block.update(
            {
                "provider": settings.embedding_provider,
                "model": model_name,
                "cache_hits": embedding_model.cache_hits,
                "cache_misses": embedding_model.cache_misses,
            }
        )

    trace: dict = {}
    retrieval_fn = build_retrieval_fn(mode, top_k, embedding_model, trace=trace)

    case_results: list[dict] = []
    for index, case in enumerate(cases, start=1):
        trace.pop("correction", None)
        outcome = run_case(case["question"], retrieval_fn, case["evidence"])
        extra: dict = {}
        if "original_question" in case:
            extra["original_question"] = case["original_question"]
            extra["perturbations"] = case["perturbations"]
        if "correction" in trace:
            extra["correction"] = trace["correction"]
        case_results.append(
            {
                "id": case["id"],
                "question": case["question"],
                **extra,
                "source": case["source"],
                "question_type": case["question_type"],
                "diacritics": diacritics_group(case["question"]),
                "first_hit_rank": outcome["first_hit_rank"],
                "matched_term": outcome["matched_term"],
                "retrieved": outcome["retrieved"],
                "coverage": outcome["coverage"],
                "split": case["split"],
                "evidence_groups": len(case["evidence"]),
                "all_groups_rank": outcome["all_groups_rank"],
            }
        )
        print(
            f"\r[{index}/{len(cases)}] {case['id'][:36]:<36}",
            end="",
            file=sys.stderr,
            flush=True,
        )
    print(file=sys.stderr)

    if embedding_model is not None:
        embedding_block["cache_hits"] = embedding_model.cache_hits
        embedding_block["cache_misses"] = embedding_model.cache_misses

    report = {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "git": git_info(),
        "dataset": {"cases": len(cases)},
        "embedding": embedding_block,
        "corpus": snapshot_corpus(),
        "config": snapshot_config(),
        "eval": {"top_k": top_k, "metric_ks": list(METRIC_KS)},
        "metrics": aggregate_metrics(case_results),
        "cases": case_results,
    }
    return report


def apply_perturbation(cases: list[dict], mode: str, seed: int) -> list[dict]:
    """Thay ``question`` bằng biến thể lỗi (giữ ``original_question``, ``perturbations``)."""

    if mode == "none":
        return cases
    from scripts.typo_variants import perturb_question

    perturbed = []
    for case in cases:
        question, applied = perturb_question(case["question"], mode, seed, case["id"])
        perturbed.append(
            {**case, "question": question, "original_question": case["question"], "perturbations": applied}
        )
    return perturbed


def evaluate_with_dataset(
    mode: str,
    dataset_path: Path,
    top_k: int,
    cache_file: Path,
    limit: int | None,
    perturb: str = "none",
    seed: int = 0,
    split: str | None = None,
) -> tuple[dict, Path]:
    dataset = load_cases(dataset_path)
    cases, skipped = select_cases(dataset, split)
    if limit:
        cases = cases[:limit]
    cases = apply_perturbation(cases, perturb, seed)
    report = evaluate(mode, cases, top_k, cache_file)
    report["dataset"] = {
        "path": str(dataset_path),
        "cases": len(cases),
        "sha256": dataset_sha256(dataset_path),
        "perturb": {"mode": perturb, "seed": seed if perturb in ("typo", "strip_partial") else None},
        "schema_version": dataset.schema_version,
        "name": dataset.name,
        "split": split,
        "skipped_no_evidence": skipped,
    }
    return report, dataset_path


def write_report(report: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def format_metric_line(label: str, metrics: dict, names: tuple[str, ...]) -> str:
    values = "  ".join(f"{name} {metrics.get(name, 0.0):.3f}" for name in names)
    return f"  {label:<24} {values}"


def print_summary(report: dict) -> None:
    corpus = report["corpus"]
    git = report["git"]
    print(
        f"mode={report['mode']} top_k={report['eval']['top_k']} "
        f"cases={report['dataset']['cases']} elapsed={report['elapsed_seconds']}s"
    )
    print(
        f"corpus fingerprint={corpus['fingerprint'][:16]}… "
        f"({corpus['documents']} tài liệu, {corpus['chunks']} chunk, "
        f"{corpus['embedded_chunks']} đã embed)"
    )
    if git.get("commit"):
        print(f"git commit={git['commit'][:12]} branch={git.get('branch')} dirty={git.get('dirty')}")
    embedding = report["embedding"]
    if embedding.get("model"):
        print(
            f"embedding model={embedding['model']} "
            f"(cache {embedding['cache_hits']} hit / {embedding['cache_misses']} miss)"
        )
    print()
    skipped = report["dataset"].get("skipped_no_evidence") or []
    if skipped:
        print(f"bỏ qua {len(skipped)} câu không có bằng chứng (không có đáp án / chỉ chấm claim)")
    for section_metrics, names in (
        (report["metrics"]["overall"], RANK_METRICS),
        (report["metrics"]["overall"], COVERAGE_METRICS),
        (report["metrics"]["overall"], ALL_GROUPS_METRICS),
    ):
        print(format_metric_line("overall", section_metrics, names))
    for section in ("by_diacritics", "by_question_type", "by_source"):
        groups = report["metrics"].get(section) or {}
        if not groups:
            continue
        print(section)
        for label, metrics in groups.items():
            print(format_metric_line(label, metrics, RANK_METRICS))
            print(format_metric_line(label, metrics, COVERAGE_METRICS))
            print(format_metric_line(label, metrics, ALL_GROUPS_METRICS))
    print_dominance(report_dominance(report))


def report_dominance(report: dict) -> dict:
    """Lấy section_dominance từ báo cáo; báo cáo schema cũ thì tính lại từ `cases`."""

    stored = (report.get("metrics") or {}).get("section_dominance")
    return stored if stored else section_dominance(report.get("cases") or [])


def print_dominance(dominance: dict, limit: int = 5, label: str = "") -> None:
    print(f"section_dominance{label} (tỉ lệ câu có section trong top-{dominance['k']}):")
    for entry in dominance["top"][:limit]:
        print(f"  {entry['share']:.3f}  ({entry['cases']} câu)  {entry['section'][:110]}")


# ---------------------------------------------------------------------------
# So sánh hai báo cáo
# ---------------------------------------------------------------------------


def collect_metric_rows(metrics: dict) -> dict[str, dict[str, float | None]]:
    """Duỗi metrics thành dict {đường_dẫn: {metric: giá trị}} cho bảng so sánh.

    Chỉ giữ các metric thực sự có trong báo cáo để so sánh chéo báo cáo schema cũ
    (thiếu coverage) với schema mới mà không tạo giá trị 0 giả.
    """

    def metric_row(source: dict) -> dict[str, float | None]:
        return {name: source[name] for name in REPORT_METRICS if name in source}

    rows: dict[str, dict[str, float | None]] = {}
    overall = metrics.get("overall") or {}
    rows["overall"] = metric_row(overall)
    for section in ("by_diacritics", "by_question_type", "by_source"):
        for label, group_metrics in (metrics.get(section) or {}).items():
            rows[f"{section}.{label}"] = metric_row(group_metrics)
    return rows


def compare_reports(path_a: Path, path_b: Path) -> int:
    reports = []
    for path in (path_a, path_b):
        try:
            reports.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Lỗi: không đọc được báo cáo {path}: {exc}", file=sys.stderr)
            return 2
    report_a, report_b = reports

    def describe(path: Path, report: dict) -> str:
        corpus = report.get("corpus") or {}
        git = report.get("git") or {}
        dataset = report.get("dataset") or {}
        return (
            f"{path.name}: mode={report.get('mode')} cases={dataset.get('cases')} "
            f"top_k={(report.get('eval') or {}).get('top_k')} "
            f"commit={(git.get('commit') or '?')[:12]} "
            f"corpus={str(corpus.get('fingerprint', '?'))[:12]} "
            f"lúc={report.get('created_at')}"
        )

    print(f"A: {describe(path_a, report_a)}")
    print(f"B: {describe(path_b, report_b)}")

    fingerprints = {
        report_a.get("corpus", {}).get("fingerprint"),
        report_b.get("corpus", {}).get("fingerprint"),
    }
    if len(fingerprints) > 1:
        print("Cảnh báo: hai báo cáo dùng kho tài liệu (fingerprint) khác nhau.")
    dataset_hashes = {
        report_a.get("dataset", {}).get("sha256"),
        report_b.get("dataset", {}).get("sha256"),
    }
    if len(dataset_hashes) > 1:
        print("Cảnh báo: hai báo cáo dùng dataset khác nhau.")
    if report_a.get("schema_version") != report_b.get("schema_version"):
        print(
            f"Chú thích: schema_version khác nhau "
            f"({report_a.get('schema_version')} vs {report_b.get('schema_version')}); "
            "metric chỉ có ở một bên hiển thị '—'."
        )

    rows_a = collect_metric_rows(report_a.get("metrics") or {})
    rows_b = collect_metric_rows(report_b.get("metrics") or {})
    all_keys = sorted(set(rows_a) | set(rows_b), key=lambda key: (key != "overall", key))

    cases_a = (report_a.get("metrics", {}).get("overall") or {}).get("cases")
    cases_b = (report_b.get("metrics", {}).get("overall") or {}).get("cases")
    print()
    header = f"{'nhóm':<38} {'metric':<13} {'A':>8} {'B':>8} {'delta':>9}"
    print(header)
    print("-" * len(header))
    for key in all_keys:
        metrics_a = rows_a.get(key, {})
        metrics_b = rows_b.get(key, {})
        for name in REPORT_METRICS:
            value_a = metrics_a.get(name)
            value_b = metrics_b.get(name)
            if value_a is None and value_b is None:
                continue
            text_a = f"{value_a:.3f}" if value_a is not None else "—"
            text_b = f"{value_b:.3f}" if value_b is not None else "—"
            if value_a is not None and value_b is not None:
                delta = f"{value_b - value_a:+.3f}"
            else:
                delta = "—"
            suffix = f"  (n={cases_a})" if name == "hit@1" and cases_a == cases_b else ""
            print(f"{key:<38} {name:<13} {text_a:>8} {text_b:>8} {delta:>9}{suffix}")

    dominance_a = report_dominance(report_a)
    dominance_b = report_dominance(report_b)
    print()
    print(
        f"{'section_dominance max':<38} {'share':<13} {dominance_a['max_share']:>8.3f} "
        f"{dominance_b['max_share']:>8.3f} {dominance_b['max_share'] - dominance_a['max_share']:>+9.3f}"
    )
    print_dominance(dominance_a, label=" A")
    print_dominance(dominance_b, label=" B")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Đánh giá retrieval offline (hit@k, MRR) không cần LLM judge.",
    )
    parser.add_argument("--mode", choices=MODES, default="hybrid", help="Chế độ retrieval cần đo.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET, help="File dataset JSON.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=max(METRIC_KS),
        help="Số context lấy về trong một lần chạy (mặc định 10 để tính hit@10).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"File báo cáo JSON (mặc định {DEFAULT_OUTPUT_DIR / 'baseline_<mode>.json'}).",
    )
    parser.add_argument(
        "--embedding-cache",
        type=Path,
        default=DEFAULT_CACHE_FILE,
        help=f"File cache embedding (mặc định {DEFAULT_CACHE_FILE}).",
    )
    parser.add_argument("--limit", type=int, help="Chỉ chạy N câu đầu (debug nhanh).")
    parser.add_argument("--split", choices=SPLITS, help="Chỉ chạy câu thuộc split này (dataset v2).")
    add_perturb_arguments(parser)
    parser.add_argument(
        "--compare",
        nargs=2,
        type=Path,
        metavar=("A.json", "B.json"),
        help="In bảng chênh lệch giữa hai báo cáo rồi thoát, không chạy đánh giá.",
    )
    args = parser.parse_args(argv)
    if args.compare is None and not 1 <= args.top_k <= 20:
        parser.error("--top-k phải nằm trong 1..20")
    return args


def add_perturb_arguments(parser: argparse.ArgumentParser) -> None:
    from scripts.typo_variants import PERTURB_MODES

    parser.add_argument(
        "--perturb",
        choices=PERTURB_MODES,
        default="none",
        help=(
            "Biến thể câu hỏi sinh lúc chạy: bỏ hết dấu, bỏ dấu một nửa số chữ có dấu "
            "hoặc 1–3 lỗi gõ mỗi câu (không ghi fixture)."
        ),
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_PERTURB_SEED, help="Seed cho --perturb strip_partial|typo.")


def resolve_output(output: Path | None, mode: str) -> Path:
    if output is not None:
        return output if output.is_absolute() else REPO_ROOT / output
    return DEFAULT_OUTPUT_DIR / f"baseline_{mode}.json"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # Console Windows mặc định cp1252 không in được tiếng Việt khi stdout bị chuyển hướng.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.compare is not None:
        return compare_reports(args.compare[0], args.compare[1])

    report, dataset_path = evaluate_with_dataset(
        args.mode, args.dataset, args.top_k, args.embedding_cache, args.limit, args.perturb, args.seed, args.split
    )
    output = resolve_output(args.output, args.mode)
    write_report(report, output)

    print_summary(report)
    print(f"\nBáo cáo: {output}")
    print(f"Dataset: {dataset_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

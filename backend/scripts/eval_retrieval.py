"""Đánh giá retrieval offline: hit@k, MRR trên bộ câu hỏi có `expected_terms`.

Chỉ chạy phần truy xuất, không sinh câu trả lời và không gọi LLM judge. Các chế độ:

- ``bm25``: tìm từ khóa BM25 trên chunk con, gộp về chunk cha.
- ``vector``: tìm pgvector, gộp về chunk cha.
- ``hybrid``: đúng pipeline `Retriever.retrieve` (RRF vector + BM25, gộp cha).
- ``full``: hybrid + multi-query + rerank theo cấu hình hiện tại (bỏ guardrail scope
  và lọc strong_context vì không thuộc về retrieval).

Chỉ số:

- hit@1/4/10 + MRR theo rank context đầu tiên chứa một `expected_terms`.
- coverage@1/4/10: tỉ lệ `expected_terms` được phủ bởi top-k context (recall theo
  term) — đo việc truy xuất đủ mọi thông tin cần cho câu trả lời, không chỉ một.

Câu hỏi được xem là trúng khi một `expected_terms` xuất hiện trong text của context
sau khi chuẩn hóa NFKC + bỏ thẻ HTML + casefold; nhãn không phụ thuộc chunk ID nên
dùng được khi thay đổi chunking. Embedding câu hỏi được cache theo khóa
(provider, model, text) để chạy lại không tốn API.

Ví dụ::

    python -m scripts.eval_retrieval --mode hybrid
    python -m scripts.eval_retrieval --mode full --output documents/rag-eval/full.json
    python -m scripts.eval_retrieval --compare a.json b.json
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any, Callable

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_DATASET = BACKEND_DIR / "tests" / "fixtures" / "ptit_ragas_100.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "documents" / "rag-eval"
DEFAULT_CACHE_FILE = BACKEND_DIR / "storage" / "eval" / "embedding_cache.json"
MODES = ("bm25", "vector", "hybrid", "full")
METRIC_KS = (1, 4, 10)
SCHEMA_VERSION = 2
RANK_METRICS = ("hit@1", "hit@4", "hit@10", "mrr")
COVERAGE_METRICS = ("coverage@1", "coverage@4", "coverage@10")
REPORT_METRICS = RANK_METRICS + COVERAGE_METRICS

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
VIETNAMESE_DIACRITICS = set(
    "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộ"
    "ơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
)
UNKNOWN_GROUP = "unknown"

CONFIG_FIELDS = (
    "chunk_size",
    "chunk_overlap",
    "parent_child_chunking_enabled",
    "child_chunk_size",
    "child_chunk_overlap",
    "hybrid_vector_weight",
    "hybrid_candidate_multiplier",
    "hybrid_rrf_k",
    "retrieval_min_vector_score",
    "retrieval_min_bm25_score",
    "query_rewrite_use_llm",
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


def normalize_text(text: str) -> str:
    """Chuẩn hóa để so khớp: NFKC, bỏ thẻ HTML, gộp khoảng trắng, casefold."""

    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    # NFKC trước để các ký tự full-width như ＜ trở thành < rồi mới lọc thẻ.
    normalized = HTML_TAG_RE.sub(" ", normalized)
    normalized = html.unescape(normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized)
    return normalized.casefold().strip()


def normalize_terms(expected_terms: list[str]) -> list[tuple[str, str]]:
    """Chuẩn hóa danh sách term, giữ cả bản gốc để ghi vào báo cáo."""

    pairs: list[tuple[str, str]] = []
    for term in expected_terms:
        normalized = normalize_text(str(term))
        if normalized:
            pairs.append((normalized, str(term)))
    return pairs


def first_hit_rank(
    contexts: list[dict],
    expected_terms: list[str],
    text_field: str = "text",
) -> tuple[int | None, str | None]:
    """Tìm rank context đầu tiên chứa một term kỳ vọng.

    Trả về ``(rank_bắt_đầu_từ_1, term_gốc)``; ``(None, None)`` nếu không trúng.
    """

    terms = normalize_terms(expected_terms)
    if not terms:
        return None, None
    for rank, context in enumerate(contexts, start=1):
        text = normalize_text(str(context.get(text_field) or ""))
        if not text:
            continue
        for normalized, original in terms:
            if normalized in text:
                return rank, original
    return None, None


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

    terms = [normalized for normalized, _ in normalize_terms(expected_terms)]
    if not terms:
        return {f"coverage@{k}": 0.0 for k in ks}
    normalized_texts = [
        normalize_text(str(context.get(text_field) or "")) for context in contexts
    ]
    metrics: dict[str, float] = {}
    for k in ks:
        prefix = [text for text in normalized_texts[:k] if text]
        covered = sum(1 for term in terms if any(term in text for text in prefix))
        metrics[f"coverage@{k}"] = round(covered / len(terms), 6)
    return metrics


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


def case_group_value(case: dict, *keys: str) -> str:
    """Lấy nhóm từ metadata câu hỏi; dataset hiện có thể chưa có các trường này."""

    for key in keys:
        value = str(case.get(key) or "").strip()
        if value:
            return value
    return UNKNOWN_GROUP


def aggregate_metrics(case_results: list[dict]) -> dict:
    """Gộp chỉ số tổng và theo nhóm nguồn / loại câu hỏi / dấu."""

    def summarize(items: list[dict]) -> dict:
        metrics = compute_metrics([item["first_hit_rank"] for item in items])
        metrics.update(
            compute_coverage_metrics([item.get("coverage") or {} for item in items])
        )
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

    return {"overall": summarize(case_results), **grouped}


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
    def cache_key(provider: str, model: str, text: str) -> str:
        material = f"{provider}\x00{model}\x00{text}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float] | None] = [None] * len(texts)
        missing: list[tuple[int, str, str]] = []
        for index, text in enumerate(texts):
            key = self.cache_key(self.provider, self.model, text)
            cached = self._cache.get(key)
            if cached is not None:
                results[index] = cached
                self.cache_hits += 1
            else:
                missing.append((index, key, text))

        if missing:
            vectors = self.inner.embed([text for _, _, text in missing])
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


def load_dataset(path: Path) -> list[dict]:
    """Nạp dataset JSON: mảng câu hỏi, hoặc object có khóa data/samples/cases/questions."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        for key in ("data", "samples", "cases", "questions"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path} phải chứa mảng câu hỏi không rỗng")

    cases: list[dict] = []
    for number, raw in enumerate(payload, start=1):
        question = str(raw.get("question") or raw.get("user_input") or "").strip()
        terms = raw.get("expected_terms") or []
        if isinstance(terms, str):
            terms = [terms]
        if not question:
            raise ValueError(f"Câu thứ {number} trong {path} thiếu `question`")
        if not terms:
            raise ValueError(f"Câu {raw.get('id', number)!r} thiếu `expected_terms`")
        cases.append(
            {
                "id": str(raw.get("id") or f"case_{number:04d}"),
                "question": question,
                "expected_terms": [str(term) for term in terms],
                "source": case_group_value(raw, "source", "source_document", "document"),
                "question_type": case_group_value(raw, "question_type"),
            }
        )
    return cases


def dataset_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Xây pipeline retrieval theo chế độ
# ---------------------------------------------------------------------------


def build_retrieval_fn(
    mode: str,
    top_k: int,
    embedding_model: Any | None,
) -> Callable[[str], list[dict]]:
    """Dựng hàm retrieval dùng đúng component của app cho từng chế độ."""

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
            query_embedding = embedding_model.embed([query])[0]
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
    uses_llm_queries = settings.query_rewrite_use_llm or (
        settings.multi_query_enabled and settings.multi_query_use_llm
    )
    if uses_llm_queries:
        print(
            "Cảnh báo: query rewrite/multi-query dùng LLM nên kết quả có thể không lặp lại được.",
            file=sys.stderr,
        )

    def retrieve_full(query: str) -> list[dict]:
        rewritten = rewriter.rewrite(query, history=None)
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

    Với chế độ full dùng LLM cho rewrite/multi-query thì không đoán trước được,
    trả rỗng và để cache hoạt động per-call.
    """

    if mode in ("bm25",):
        return []
    if mode in ("vector", "hybrid"):
        return list(questions)

    from app.core.config import settings

    if settings.query_rewrite_use_llm or (
        settings.multi_query_enabled and settings.multi_query_use_llm
    ):
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


def run_case(question: str, retrieval_fn: Callable[[str], list[dict]], expected_terms: list[str]) -> dict:
    contexts = retrieval_fn(question)
    rank, matched_term = first_hit_rank(contexts, expected_terms)
    retrieved = []
    for position, context in enumerate(contexts[: max(METRIC_KS)], start=1):
        retrieved.append(
            {
                "rank": position,
                "chunk_id": str(context.get("chunk_id") or ""),
                "source_name": str(context.get("source_name") or ""),
                "heading": str(context.get("heading") or ""),
                "score": round(float(context.get("score") or 0.0), 6),
            }
        )
    return {
        "first_hit_rank": rank,
        "matched_term": matched_term,
        "retrieved": retrieved,
        "coverage": coverage_by_k(contexts, expected_terms),
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
            embedding_model.embed(warm_texts)
        embedding_block.update(
            {
                "provider": settings.embedding_provider,
                "model": model_name,
                "cache_hits": embedding_model.cache_hits,
                "cache_misses": embedding_model.cache_misses,
            }
        )

    retrieval_fn = build_retrieval_fn(mode, top_k, embedding_model)

    case_results: list[dict] = []
    for index, case in enumerate(cases, start=1):
        outcome = run_case(case["question"], retrieval_fn, case["expected_terms"])
        case_results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "source": case["source"],
                "question_type": case["question_type"],
                "diacritics": diacritics_group(case["question"]),
                "first_hit_rank": outcome["first_hit_rank"],
                "matched_term": outcome["matched_term"],
                "retrieved": outcome["retrieved"],
                "coverage": outcome["coverage"],
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


def evaluate_with_dataset(mode: str, dataset_path: Path, top_k: int, cache_file: Path, limit: int | None) -> tuple[dict, Path]:
    cases = load_dataset(dataset_path)
    if limit:
        cases = cases[:limit]
    report = evaluate(mode, cases, top_k, cache_file)
    report["dataset"] = {
        "path": str(dataset_path),
        "cases": len(cases),
        "sha256": dataset_sha256(dataset_path),
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
    for section_metrics, names in (
        (report["metrics"]["overall"], RANK_METRICS),
        (report["metrics"]["overall"], COVERAGE_METRICS),
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
    header = f"{'nhóm':<38} {'metric':<8} {'A':>8} {'B':>8} {'delta':>9}"
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
            print(f"{key:<38} {name:<8} {text_a:>8} {text_b:>8} {delta:>9}{suffix}")
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


def resolve_output(output: Path | None, mode: str) -> Path:
    if output is not None:
        return output if output.is_absolute() else REPO_ROOT / output
    return DEFAULT_OUTPUT_DIR / f"baseline_{mode}.json"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.compare is not None:
        return compare_reports(args.compare[0], args.compare[1])

    report, dataset_path = evaluate_with_dataset(
        args.mode, args.dataset, args.top_k, args.embedding_cache, args.limit
    )
    output = resolve_output(args.output, args.mode)
    write_report(report, output)

    print_summary(report)
    print(f"\nBáo cáo: {output}")
    print(f"Dataset: {dataset_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

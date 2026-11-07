"""Đo tín hiệu confidence gate trên câu có đáp án và câu không có đáp án (RAG-18).

Chạy cùng pipeline `eval_retrieval --mode full` (query rewrite + multi-query theo luật,
hybrid, rerank theo cấu hình; không gọi LLM) rồi ghi cho từng câu:

- kết quả scope guardrail (`check_scope`);
- tín hiệu top-1 = max trên các context sau rerank: `vector` (cosine), `bm25` (thô),
  `bm25_norm` (BM25 chuẩn hóa [0, 1]), `rerank`;
- rank context đầu tiên chứa `expected_terms` (câu có đáp án);
- quyết định của gate cũ (vector ≥ min_vector OR bm25 thô ≥ min_bm25) và gate đang cài.

`--sweep` quét lưới ngưỡng cho từng luật kết hợp và in tỉ lệ từ chối nhầm (câu có đáp
án) / từ chối đúng (câu không có đáp án). Ví dụ::

    python -m scripts.eval_confidence --output ../documents/rag-eval/rag-18/local.json --sweep
    python -m scripts.eval_confidence --set multi_query_enabled=true --set reranker_enabled=true \
        --set reranker_provider=heuristic --sweep
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from scripts.eval_retrieval import (
    BACKEND_DIR,
    DEFAULT_CACHE_FILE,
    CachedEmbeddingModel,
    build_retrieval_fn,
    dataset_sha256,
    first_hit_rank,
    git_info,
    snapshot_config,
    snapshot_corpus,
    warm_cache_texts,
)

FIXTURES = BACKEND_DIR / "tests" / "fixtures"
DEFAULT_ANSWERABLE = (FIXTURES / "ptit_rag_300.json", FIXTURES / "ptit_ragas_100.json")
DEFAULT_UNANSWERABLE = FIXTURES / "ptit_no_answer_56.json"
SCHEMA_VERSION = 1
SIGNALS = ("vector", "bm25", "bm25_norm", "rerank")
SIGNAL_FIELDS = {
    "vector": "vector_score",
    "bm25": "bm25_score",
    "bm25_norm": "bm25_norm_score",
    "rerank": "rerank_score",
}
PERCENTILES = (5, 10, 25, 50, 75, 90, 95)
HIT_K = 4
# Ràng buộc chọn ngưỡng: từ chối nhầm trên golden set chính không quá mức này.
MAX_FALSE_REFUSAL = 0.05
PRIMARY_DATASET = "ptit_rag_300"
EXTRA_CONFIG_FIELDS = ("embedding_provider", "embedding_model", "retrieval_min_bm25_norm_score")


# ---------------------------------------------------------------------------
# Phần tính toán thuần (không cần DB/mạng, dùng cho unit test)
# ---------------------------------------------------------------------------


def top_signals(contexts: list[dict]) -> dict[str, float | None]:
    """Tín hiệu top-1 của từng loại: max trên các context, None nếu không context nào có."""

    signals: dict[str, float | None] = {}
    for name, field in SIGNAL_FIELDS.items():
        values = [float(context[field]) for context in contexts if context.get(field) is not None]
        signals[name] = max(values) if values else None
    return signals


def legacy_gate(signals: dict, min_vector: float, min_bm25: float) -> bool:
    """Gate cũ: một chunk vượt cosine hoặc BM25 thô là đủ (trên top-1 tương đương)."""

    vector, bm25 = signals.get("vector"), signals.get("bm25")
    return (vector is not None and vector >= min_vector) or (bm25 is not None and bm25 >= min_bm25)


def _value(signals: dict, name: str) -> float:
    value = signals.get(name)
    return float(value) if value is not None else float("-inf")


def _frange(start: float, stop: float, step: float) -> list[float]:
    count = int(round((stop - start) / step))
    return [round(start + index * step, 4) for index in range(count + 1)]


RuleFn = Callable[[dict, dict], bool]

RULES: dict[str, tuple[RuleFn, dict[str, list[float]]]] = {
    "or_raw": (
        lambda s, p: _value(s, "vector") >= p["vector"] or _value(s, "bm25") >= p["bm25"],
        {"vector": _frange(0.20, 0.70, 0.02), "bm25": _frange(1.0, 30.0, 1.0)},
    ),
    "vector": (
        lambda s, p: _value(s, "vector") >= p["vector"],
        {"vector": _frange(0.10, 0.80, 0.01)},
    ),
    "bm25_raw": (
        lambda s, p: _value(s, "bm25") >= p["bm25"],
        {"bm25": _frange(0.0, 40.0, 0.5)},
    ),
    "bm25_norm": (
        lambda s, p: _value(s, "bm25_norm") >= p["bm25_norm"],
        {"bm25_norm": _frange(0.0, 0.90, 0.01)},
    ),
    "and": (
        lambda s, p: _value(s, "vector") >= p["vector"] and _value(s, "bm25_norm") >= p["bm25_norm"],
        {"vector": _frange(0.10, 0.80, 0.01), "bm25_norm": _frange(0.0, 0.90, 0.01)},
    ),
    "or_norm": (
        lambda s, p: _value(s, "vector") >= p["vector"] or _value(s, "bm25_norm") >= p["bm25_norm"],
        {"vector": _frange(0.10, 0.80, 0.01), "bm25_norm": _frange(0.0, 0.90, 0.01)},
    ),
    "weighted": (
        lambda s, p: p["weight"] * _value(s, "vector") + (1 - p["weight"]) * _value(s, "bm25_norm")
        >= p["threshold"],
        {"weight": [0.3, 0.4, 0.5, 0.6, 0.7], "threshold": _frange(0.10, 0.80, 0.01)},
    ),
    "rerank": (
        lambda s, p: _value(s, "rerank") >= p["rerank"],
        {"rerank": _frange(-10.0, 10.0, 0.1)},
    ),
    # Luật gate đang cài khi reranker là cross-encoder (bỏ sàn cosine vì không đổi kết quả).
    "rerank_and_norm": (
        lambda s, p: _value(s, "rerank") >= p["rerank"] and _value(s, "bm25_norm") >= p["bm25_norm"],
        {"rerank": _frange(-4.0, 2.0, 0.05), "bm25_norm": _frange(0.0, 0.50, 0.01)},
    ),
}


def percentile(values: list[float], q: float) -> float | None:
    """Percentile nội suy tuyến tính (giống numpy mặc định)."""

    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction, 6)


def summarize_signals(records: list[dict]) -> dict:
    """Percentile + số câu thiếu tín hiệu cho từng signal."""

    summary: dict[str, dict] = {}
    for name in SIGNALS:
        values = [record["signals"][name] for record in records if record["signals"].get(name) is not None]
        summary[name] = {
            "count": len(values),
            "missing": len(records) - len(values),
            **{f"p{q}": percentile(values, q) for q in PERCENTILES},
        }
    return summary


def case_groups(records: list[dict]) -> dict[str, list[dict]]:
    """Nhóm báo cáo: từng golden set, nhóm hit@4, câu không có đáp án theo category."""

    groups: dict[str, list[dict]] = {}
    for record in records:
        if record["answerable"]:
            groups.setdefault(record["dataset"], []).append(record)
            if record.get("first_hit_rank") is not None and record["first_hit_rank"] <= HIT_K:
                groups.setdefault(f"{record['dataset']}@hit{HIT_K}", []).append(record)
        else:
            groups.setdefault("no_answer", []).append(record)
            groups.setdefault(f"no_answer:{record['category']}", []).append(record)
    return dict(sorted(groups.items()))


def evaluate_decisions(records: list[dict], decide: Callable[[dict], bool]) -> dict:
    """Tỉ lệ từ chối cho một hàm quyết định gate nhận record (True = đủ context).

    - ``false_refusal[<nhóm>]``: câu có đáp án bị gate từ chối (không tính scope).
    - ``false_refusal_e2e[<nhóm>]``: tính cả câu có đáp án bị scope guardrail chặn.
    - ``refusal_gate``: câu không có đáp án lọt scope bị gate từ chối / số câu lọt scope.
    - ``refusal_e2e``: câu không có đáp án bị scope chặn hoặc gate từ chối / tổng số câu.
    """

    false_refusal: dict[str, float] = {}
    false_refusal_e2e: dict[str, float] = {}
    for group, items in case_groups(records).items():
        if group.startswith("no_answer"):
            continue
        refused = [not decide(record) for record in items]
        refused_e2e = [
            (not record["scope_allowed"]) or flag for record, flag in zip(items, refused)
        ]
        false_refusal[group] = round(sum(refused) / len(items), 6)
        false_refusal_e2e[group] = round(sum(refused_e2e) / len(items), 6)

    unanswerable = [record for record in records if not record["answerable"]]
    in_scope = [record for record in unanswerable if record["scope_allowed"]]
    refused_gate = sum(not decide(record) for record in in_scope)
    refused_e2e = sum((not record["scope_allowed"]) or (not decide(record)) for record in unanswerable)
    by_category: dict[str, float] = {}
    for category in sorted({record["category"] for record in in_scope}):
        items = [record for record in in_scope if record["category"] == category]
        by_category[category] = round(sum(not decide(record) for record in items) / len(items), 6)
    return {
        "false_refusal": false_refusal,
        "false_refusal_e2e": false_refusal_e2e,
        "refusal_gate": round(refused_gate / len(in_scope), 6) if in_scope else None,
        "refusal_gate_by_category": by_category,
        "refusal_e2e": round(refused_e2e / len(unanswerable), 6) if unanswerable else None,
        "unanswerable_in_scope": len(in_scope),
        "unanswerable_total": len(unanswerable),
    }


def _grid(params: dict[str, list[float]]) -> list[dict[str, float]]:
    combos: list[dict[str, float]] = [{}]
    for name, values in params.items():
        combos = [{**combo, name: value} for combo in combos for value in values]
    return combos


def sweep_rule(
    records: list[dict],
    rule: str,
    primary: str = PRIMARY_DATASET,
    max_false_refusal: float = MAX_FALSE_REFUSAL,
) -> dict:
    """Quét lưới một luật; trả điểm tốt nhất đạt ràng buộc và biên Pareto.

    Điểm tốt nhất: từ chối nhầm trên ``primary`` ≤ ``max_false_refusal``, tối đa
    ``refusal_gate``; hòa thì ít từ chối nhầm hơn.
    """

    decide_fn, params = RULES[rule]
    signal_names = {
        "or_raw": ("vector", "bm25"),
        "vector": ("vector",),
        "bm25_raw": ("bm25",),
        "bm25_norm": ("bm25_norm",),
        "and": ("vector", "bm25_norm"),
        "or_norm": ("vector", "bm25_norm"),
        "weighted": ("vector", "bm25_norm"),
        "rerank": ("rerank",),
        "rerank_and_norm": ("rerank", "bm25_norm"),
    }[rule]
    if not any(record["signals"].get(name) is not None for record in records for name in signal_names):
        return {"rule": rule, "available": False}

    points: list[dict] = []
    for combo in _grid(params):
        metrics = evaluate_decisions(records, lambda record, combo=combo: decide_fn(record["signals"], combo))
        points.append({"params": combo, **metrics})

    def primary_fr(point: dict) -> float:
        return point["false_refusal"].get(primary, 1.0)

    feasible = [point for point in points if primary_fr(point) <= max_false_refusal]
    best = (
        max(feasible, key=lambda point: (point["refusal_gate"] or 0.0, -primary_fr(point)))
        if feasible
        else None
    )
    # Biên Pareto theo (từ chối nhầm primary ↓, từ chối đúng ↑) để vẽ đường đánh đổi.
    frontier: list[dict] = []
    for point in sorted(points, key=lambda item: (primary_fr(item), -(item["refusal_gate"] or 0.0))):
        if not frontier or (point["refusal_gate"] or 0.0) > (frontier[-1]["refusal_gate"] or 0.0):
            frontier.append(point)
    return {"rule": rule, "available": True, "grid_size": len(points), "best": best, "frontier": frontier}


def neighborhood(records: list[dict], rule: str, params: dict[str, float], spread: float = 0.10) -> list[dict]:
    """Đánh giá luật tại ngưỡng ±spread (mỗi tham số ngưỡng một lần) để xem độ ổn định."""

    decide_fn, _ = RULES[rule]
    rows = []
    for name, value in params.items():
        if name == "weight":
            continue
        for factor in (1 - spread, 1 + spread):
            shifted = {**params, name: round(value * factor, 4)}
            metrics = evaluate_decisions(records, lambda record, p=shifted: decide_fn(record["signals"], p))
            rows.append({"params": shifted, "shifted": name, "factor": factor, **metrics})
    return rows


def histogram(values: list[float], bins: int = 10, lower: float | None = None, upper: float | None = None) -> list[tuple[float, float, int]]:
    if not values:
        return []
    low = min(values) if lower is None else lower
    high = max(values) if upper is None else upper
    width = (high - low) / bins or 1.0
    counts = [0] * bins
    for value in values:
        index = min(bins - 1, max(0, int((value - low) / width)))
        counts[index] += 1
    return [(round(low + index * width, 4), round(low + (index + 1) * width, 4), count) for index, count in enumerate(counts)]


# ---------------------------------------------------------------------------
# Nạp dataset và chạy pipeline
# ---------------------------------------------------------------------------


def load_cases(path: Path) -> list[dict]:
    """Nạp câu có đáp án (có `expected_terms`) hoặc không có đáp án (`answerable: false`)."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = []
    for number, raw in enumerate(payload, start=1):
        answerable = raw.get("answerable", True) is not False
        terms = raw.get("expected_terms") or []
        if answerable and not terms:
            raise ValueError(f"Câu {raw.get('id', number)!r} trong {path} thiếu `expected_terms`")
        cases.append(
            {
                "id": str(raw.get("id") or f"case_{number:04d}"),
                "question": str(raw.get("question") or raw.get("user_input") or "").strip(),
                "answerable": answerable,
                "category": str(raw.get("category") or ("answerable" if answerable else "unknown")),
                "expected_terms": [str(term) for term in terms],
                "dataset": path.stem,
            }
        )
    return cases


def apply_overrides(pairs: list[str]) -> dict[str, Any]:
    """Ghi đè settings in-memory từ `--set key=value` (chỉ cho phiên đo)."""

    from app.core.config import settings

    applied: dict[str, Any] = {}
    for pair in pairs:
        key, _, raw = pair.partition("=")
        key = key.strip()
        if not hasattr(settings, key):
            raise SystemExit(f"Không có setting {key!r}")
        current = getattr(settings, key)
        if isinstance(current, bool):
            value: Any = raw.strip().lower() in ("1", "true", "yes", "on")
        elif isinstance(current, int):
            value = int(raw)
        elif isinstance(current, float):
            value = float(raw)
        elif current is None and raw.strip().lower() in ("", "none", "null"):
            value = None
        else:
            try:
                value = float(raw) if current is None else raw.strip()
            except ValueError:
                value = raw.strip()
        setattr(settings, key, value)
        applied[key] = value
    return applied


def run(datasets: list[Path], top_k: int, cache_file: Path) -> dict:
    from app.core.config import settings
    from app.embeddings import create_embedding_model
    from app.generation.confidence import (
        LEGACY_DEFAULT_MIN_VECTOR_SCORE,
        assess_context,
        thresholds_from_settings,
    )
    from app.guardrails import check_scope

    started = time.monotonic()
    cases = [case for path in datasets for case in load_cases(path)]
    inner = create_embedding_model()
    model_name = str(getattr(inner, "model_name", "") or settings.embedding_model)
    embedding = CachedEmbeddingModel(inner, settings.embedding_provider, model_name, cache_file)
    warm = warm_cache_texts("full", [case["question"] for case in cases])
    if warm:
        embedding.embed(warm)
    retrieval_fn = build_retrieval_fn("full", top_k, embedding)
    thresholds = thresholds_from_settings()
    # Gate cũ để so sánh: ngưỡng vector cũ (mặc định 0.30 khi chưa đặt) OR BM25 thô.
    legacy_min_vector = settings.retrieval_min_vector_score or LEGACY_DEFAULT_MIN_VECTOR_SCORE

    records: list[dict] = []
    for index, case in enumerate(cases, start=1):
        scope = check_scope(case["question"])
        contexts = retrieval_fn(case["question"])
        signals = top_signals(contexts)
        rank = None
        if case["answerable"]:
            rank, _ = first_hit_rank(contexts, case["expected_terms"])
        record = {
            "id": case["id"],
            "dataset": case["dataset"],
            "question": case["question"],
            "answerable": case["answerable"],
            "category": case["category"],
            "scope_allowed": scope.allowed,
            "scope_reason": scope.reason,
            "signals": signals,
            "first_hit_rank": rank,
            "gate_legacy": legacy_gate(signals, legacy_min_vector, settings.retrieval_min_bm25_score),
            "retrieved": [
                {
                    "rank": position,
                    "chunk_id": str(context.get("chunk_id") or ""),
                    "section_path": str(context.get("section_path") or context.get("heading") or ""),
                    "snippet": " ".join(str(context.get("evidence_text") or context.get("text") or "").split())[:200],
                }
                for position, context in enumerate(contexts[:3], start=1)
            ],
        }
        decision = assess_context(contexts, thresholds)
        record["gate"] = {"strong": decision.strong, "reason": decision.reason}
        records.append(record)
        print(f"\r[{index}/{len(cases)}] {case['id'][:36]:<36}", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)

    config = snapshot_config()
    config.update({field: getattr(settings, field, None) for field in EXTRA_CONFIG_FIELDS})
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "git": git_info(),
        "datasets": [
            {"path": str(path), "name": path.stem, "sha256": dataset_sha256(path)} for path in datasets
        ],
        "embedding": {
            "provider": settings.embedding_provider,
            "model": model_name,
            "cache_hits": embedding.cache_hits,
            "cache_misses": embedding.cache_misses,
        },
        "reranker": {"enabled": settings.reranker_enabled, "provider": settings.reranker_provider},
        "corpus": snapshot_corpus(),
        "config": config,
        "gate_thresholds": thresholds.as_dict(),
        "eval": {"top_k": top_k, "hit_k": HIT_K},
        "cases": records,
    }


def build_summary(report: dict, sweep: bool) -> dict:
    records = report["cases"]
    groups = case_groups(records)
    summary: dict[str, Any] = {
        "groups": {group: len(items) for group, items in groups.items()},
        "scope_pass": {
            group: round(sum(record["scope_allowed"] for record in items) / len(items), 6)
            for group, items in groups.items()
        },
        "distributions": {group: summarize_signals(items) for group, items in groups.items()},
        "legacy_gate": _decision_metrics(records, "gate_legacy"),
    }
    if any("gate" in record for record in records):
        summary["gate"] = _decision_metrics(records, "gate")
    if sweep:
        # rerank_score của reranker heuristic là min-max trong danh sách ứng viên: không quét ngưỡng.
        reranker = report.get("reranker") or {}
        absolute_rerank = bool(reranker.get("enabled")) and reranker.get("provider") == "cross-encoder"
        summary["sweep"] = {
            rule: sweep_rule(records, rule)
            if absolute_rerank or not rule.startswith("rerank")
            else {"rule": rule, "available": False}
            for rule in RULES
        }
        for result in summary["sweep"].values():
            if result.get("best"):
                result["neighborhood"] = neighborhood(records, result["rule"], result["best"]["params"])
    return summary


def _decision_metrics(records: list[dict], field: str) -> dict:
    """Tỉ lệ từ chối theo quyết định đã ghi sẵn trong từng record (gate thật, không mô phỏng)."""

    def decide(record: dict) -> bool:
        value = record[field]
        return bool(value["strong"] if isinstance(value, dict) else value)

    return evaluate_decisions(records, decide)


# ---------------------------------------------------------------------------
# In báo cáo
# ---------------------------------------------------------------------------


def _fmt(value: float | None, digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def print_report(report: dict, summary: dict) -> None:
    corpus = report["corpus"]
    print(
        f"embedding={report['embedding']['model']} reranker={report['reranker']} top_k={report['eval']['top_k']} "
        f"corpus={corpus['fingerprint'][:16]}… ({corpus['documents']} tài liệu, {corpus['chunks']} chunk) "
        f"git={str(report['git'].get('commit'))[:12]} dirty={report['git'].get('dirty')}"
    )
    print("\nPhân bố tín hiệu top-1 (p5 / p25 / p50 / p75 / p95; thiếu):")
    for group, distribution in summary["distributions"].items():
        print(f"  {group} (n={summary['groups'][group]}, scope pass {summary['scope_pass'][group]:.2f})")
        for name in SIGNALS:
            stats = distribution[name]
            if not stats["count"]:
                continue
            values = " / ".join(_fmt(stats[f"p{q}"]) for q in (5, 25, 50, 75, 95))
            print(f"    {name:<10} {values}   thiếu {stats['missing']}")

    for name, lower, upper in (("vector", 0.0, 0.8), ("bm25_norm", 0.0, 1.0)):
        print(f"\nHistogram {name}:")
        answerable = [r["signals"][name] for r in report["cases"] if r["answerable"] and r["signals"][name] is not None]
        unanswerable = [
            r["signals"][name]
            for r in report["cases"]
            if not r["answerable"] and r["scope_allowed"] and r["signals"][name] is not None
        ]
        hist_a = histogram(answerable, 16, lower, upper)
        hist_u = histogram(unanswerable, 16, lower, upper)
        for (low, high, count_a), (_, _, count_u) in zip(hist_a, hist_u):
            share_a = count_a / max(len(answerable), 1)
            share_u = count_u / max(len(unanswerable), 1)
            print(f"  [{low:.2f},{high:.2f})  có đáp án {share_a:5.1%} {'#' * round(share_a * 60):<20} "
                  f"không {share_u:5.1%} {'+' * round(share_u * 60)}")

    def print_metrics(label: str, metrics: dict) -> None:
        fr = metrics["false_refusal"]
        fr_e2e = metrics["false_refusal_e2e"]
        parts = "  ".join(f"{group} {fr[group]:.3f}/{fr_e2e[group]:.3f}" for group in fr)
        print(
            f"  {label:<44} từ chối đúng gate {_fmt(metrics['refusal_gate'])} e2e {_fmt(metrics['refusal_e2e'])}"
            f" | từ chối nhầm (gate/e2e) {parts}"
        )

    print("\nGate đã ghi:")
    print_metrics("legacy (vector OR bm25 thô)", summary["legacy_gate"])
    if "gate" in summary:
        print_metrics("gate hiện tại (assess_context)", summary["gate"])

    if "sweep" in summary:
        print(f"\nQuét ngưỡng (từ chối nhầm {PRIMARY_DATASET} ≤ {MAX_FALSE_REFUSAL:.0%}, tối đa từ chối đúng):")
        for rule, result in summary["sweep"].items():
            if not result.get("available"):
                print(f"  {rule:<10} (không có tín hiệu)")
                continue
            best = result["best"]
            if best is None:
                print(f"  {rule:<10} không điểm nào đạt ràng buộc")
                continue
            params = ", ".join(f"{key}={value}" for key, value in best["params"].items())
            print_metrics(f"{rule:<10} {params}", best)
            for row in result.get("neighborhood", []):
                shifted = f"{row['shifted']}×{row['factor']:.1f}={row['params'][row['shifted']]}"
                print(
                    f"      {shifted:<28} từ chối đúng {_fmt(row['refusal_gate'])}"
                    f"  từ chối nhầm {PRIMARY_DATASET} {row['false_refusal'].get(PRIMARY_DATASET, 0):.3f}"
                )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", action="append", type=Path, help="Dataset JSON (lặp được); mặc định 3 bộ RAG-18")
    parser.add_argument("--top-k", type=int, default=None, help="Mặc định RETRIEVAL_DEFAULT_TOP_K")
    parser.add_argument("--cache-file", type=Path, default=DEFAULT_CACHE_FILE)
    parser.add_argument("--set", dest="overrides", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--sweep", action="store_true", help="Quét lưới ngưỡng cho từng luật")
    parser.add_argument("--output", type=Path, help="Ghi báo cáo JSON")
    parser.add_argument("--from-report", type=Path, help="Bỏ qua bước chạy, tính lại tóm tắt từ báo cáo có sẵn")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.from_report:
        report = json.loads(args.from_report.read_text(encoding="utf-8"))
    else:
        from app.core.config import settings

        applied = apply_overrides(args.overrides)
        datasets = args.dataset or [*DEFAULT_ANSWERABLE, DEFAULT_UNANSWERABLE]
        report = run(datasets, args.top_k or settings.retrieval_default_top_k, args.cache_file)
        report["overrides"] = applied
    summary = build_summary(report, args.sweep)
    report["summary"] = summary
    print_report(report, summary)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(json.dumps(report, ensure_ascii=False, indent=1).encode("utf-8") + b"\n")
        print(f"\nĐã ghi {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

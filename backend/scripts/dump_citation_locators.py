"""Chụp locator citation (Điều/Khoản/Điểm) của context top-k và so sánh hai lần chụp (RAG-22).

Chạy cùng pipeline retrieval với ``eval_retrieval --mode full`` (cache embedding,
fingerprint kho, git) rồi ghi cho mỗi câu, mỗi context: ``chunk_id``, ``heading``,
``section_path``, ``article``, ``clauses``, ``points``, ``locator`` theo
``app.generation.citations`` của commit đang checkout, và cờ context có khóa
``legal_*`` trong metadata hay không.

Ví dụ::

    python -m scripts.dump_citation_locators --dataset tests/fixtures/ptit_rag_300.json \\
        --out ../documents/rag-eval/rag-22/locators_before_rag300.json
    python -m scripts.dump_citation_locators --diff before.json after.json --out diff.json

Phân loại khi so sánh (ghép theo ``id`` câu + ``chunk_id``):

- ``unchanged``: ``article``, ``clauses``, ``points`` như nhau.
- ``removed_non_article``: không có Điều ở cả hai bản, bản sau bỏ Khoản/Điểm.
- ``added_inherited_clause``: cùng Điều và Điểm, bản sau thêm đúng một Khoản ở đầu
  (Khoản đang mở từ chunk trước) còn lại giữ nguyên.
- ``other``: mọi thay đổi khác, cần giải thích từng trường hợp.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.eval_retrieval import (
    DEFAULT_CACHE_FILE,
    REPO_ROOT,
    CachedEmbeddingModel,
    build_retrieval_fn,
    dataset_sha256,
    git_info,
    load_dataset,
    snapshot_config,
    snapshot_corpus,
    warm_cache_texts,
)

SCHEMA_VERSION = 1
DEFAULT_TOP_K = 10
CATEGORIES = ("unchanged", "removed_non_article", "added_inherited_clause", "other")


# ---------------------------------------------------------------------------
# Phần thuần: trích locator từ context, phân loại thay đổi
# ---------------------------------------------------------------------------


def locator_rows(contexts: list[dict]) -> list[dict]:
    from app.generation.citations import numbered_contexts

    rows: list[dict] = []
    for rank, (context, (citation_id, citation)) in enumerate(
        zip(contexts, numbered_contexts(contexts)), start=1
    ):
        rows.append(
            {
                "rank": rank,
                "chunk_id": str(context.get("chunk_id") or ""),
                "parent_id": str(context.get("parent_id") or ""),
                "citation_id": citation_id,
                "heading": citation.get("heading"),
                "section_path": citation.get("section_path"),
                "article": citation.get("article"),
                "clauses": list(citation.get("clauses") or []),
                "points": list(citation.get("points") or []),
                "locator": citation.get("locator"),
                "has_legal_metadata": "legal_clauses" in context,
            }
        )
    return rows


def classify_change(before: dict, after: dict) -> str:
    article_b, article_a = before.get("article"), after.get("article")
    clauses_b, clauses_a = list(before.get("clauses") or []), list(after.get("clauses") or [])
    points_b, points_a = list(before.get("points") or []), list(after.get("points") or [])

    if (article_b, clauses_b, points_b) == (article_a, clauses_a, points_a):
        return "unchanged"
    if not article_b and not article_a and not clauses_a and not points_a:
        return "removed_non_article"
    if (
        article_b
        and article_a == article_b
        and points_a == points_b
        and len(clauses_a) == len(clauses_b) + 1
        and clauses_a[1:] == clauses_b
        and clauses_a[0] not in clauses_b
    ):
        return "added_inherited_clause"
    return "other"


def keeps_article_units(before: dict, after: dict) -> bool:
    """Điều kiện AC-05: citation có Điều ở bản trước giữ Điều và không mất Khoản."""

    if not before.get("article"):
        return True
    return after.get("article") == before.get("article") and set(before.get("clauses") or []) <= set(
        after.get("clauses") or []
    )


def summarize_rows(cases: list[dict]) -> dict:
    rows = [row for case in cases for row in case.get("contexts") or []]
    return {
        "contexts": len(rows),
        "with_article": sum(1 for row in rows if row.get("article")),
        "with_clauses": sum(1 for row in rows if row.get("clauses")),
        "with_points": sum(1 for row in rows if row.get("points")),
        "with_clauses_outside_article": sum(
            1 for row in rows if not row.get("article") and (row.get("clauses") or row.get("points"))
        ),
        "with_legal_metadata": sum(1 for row in rows if row.get("has_legal_metadata")),
    }


def diff_dumps(before: dict, after: dict) -> dict:
    after_cases = {case["id"]: case for case in after.get("cases") or []}
    counts = {category: 0 for category in CATEGORIES}
    changes: list[dict] = []
    violations: list[dict] = []
    unmatched: list[dict] = []
    order_changed: list[str] = []

    for case in before.get("cases") or []:
        other = after_cases.get(case["id"])
        if other is None:
            unmatched.append({"id": case["id"], "reason": "case_missing_after"})
            continue
        before_rows = case.get("contexts") or []
        after_rows = {row["chunk_id"]: row for row in other.get("contexts") or []}
        if [row["chunk_id"] for row in before_rows] != [row["chunk_id"] for row in other.get("contexts") or []]:
            order_changed.append(case["id"])
        for row in before_rows:
            match = after_rows.get(row["chunk_id"])
            if match is None:
                unmatched.append({"id": case["id"], "chunk_id": row["chunk_id"], "reason": "chunk_missing_after"})
                continue
            category = classify_change(row, match)
            counts[category] += 1
            if category != "unchanged":
                changes.append(
                    {
                        "id": case["id"],
                        "chunk_id": row["chunk_id"],
                        "category": category,
                        "section_path": row.get("section_path"),
                        "before": _locator_fields(row),
                        "after": _locator_fields(match),
                    }
                )
            if not keeps_article_units(row, match):
                violations.append(
                    {
                        "id": case["id"],
                        "chunk_id": row["chunk_id"],
                        "before": _locator_fields(row),
                        "after": _locator_fields(match),
                    }
                )

    # Cùng một chunk có thể xuất hiện ở nhiều câu; gom để đếm thay đổi duy nhất.
    unique_changes: dict[str, dict] = {}
    for change in changes:
        unique_changes.setdefault(change["chunk_id"], change)
    unique_counts = {category: 0 for category in CATEGORIES if category != "unchanged"}
    for change in unique_changes.values():
        unique_counts[change["category"]] += 1

    return {
        "before": _describe(before),
        "after": _describe(after),
        "pairs": sum(counts.values()),
        "counts": counts,
        "unique_changed_chunks": unique_counts,
        "summary_before": summarize_rows(before.get("cases") or []),
        "summary_after": summarize_rows(after.get("cases") or []),
        "ac05_violations": violations,
        "order_changed_cases": order_changed,
        "unmatched": unmatched,
        "changes": changes,
    }


def _locator_fields(row: dict) -> dict:
    return {
        "article": row.get("article"),
        "clauses": row.get("clauses") or [],
        "points": row.get("points") or [],
        "locator": row.get("locator"),
        "has_legal_metadata": bool(row.get("has_legal_metadata")),
    }


def _describe(dump: dict) -> dict:
    return {
        "created_at": dump.get("created_at"),
        "git": dump.get("git"),
        "corpus": dump.get("corpus"),
        "dataset": dump.get("dataset"),
        "top_k": dump.get("top_k"),
    }


# ---------------------------------------------------------------------------
# Chạy retrieval và ghi bản chụp
# ---------------------------------------------------------------------------


def dump_locators(dataset_path: Path, top_k: int, cache_file: Path, limit: int | None = None) -> dict:
    from app.core.config import settings
    from app.embeddings import create_embedding_model

    started = time.monotonic()
    cases = load_dataset(dataset_path)
    if limit:
        cases = cases[:limit]

    inner = create_embedding_model()
    model_name = str(getattr(inner, "model_name", "") or settings.embedding_model)
    embedding_model = CachedEmbeddingModel(inner, settings.embedding_provider, model_name, cache_file)
    warm_texts = warm_cache_texts("full", [case["question"] for case in cases])
    if warm_texts:
        embedding_model.embed(warm_texts)
    retrieval_fn = build_retrieval_fn("full", top_k, embedding_model)

    results: list[dict] = []
    for index, case in enumerate(cases, start=1):
        contexts = retrieval_fn(case["question"])
        results.append({"id": case["id"], "question": case["question"], "contexts": locator_rows(contexts)})
        print(f"\r[{index}/{len(cases)}] {case['id'][:36]:<36}", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)

    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "full",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "git": git_info(),
        "dataset": {"path": str(dataset_path), "cases": len(cases), "sha256": dataset_sha256(dataset_path)},
        "embedding": {
            "provider": settings.embedding_provider,
            "model": model_name,
            "cache_file": str(cache_file),
            "cache_hits": embedding_model.cache_hits,
            "cache_misses": embedding_model.cache_misses,
        },
        "corpus": snapshot_corpus(),
        "config": snapshot_config(),
        "top_k": top_k,
        "summary": summarize_rows(results),
        "cases": results,
    }


def write_json(payload: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def resolve_input(path: Path) -> Path:
    return path if path.is_absolute() or path.exists() else REPO_ROOT / path


def resolve_output(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def print_diff(diff: dict) -> None:
    for label in ("before", "after"):
        info = diff[label]
        git = info.get("git") or {}
        corpus = info.get("corpus") or {}
        print(
            f"{label}: commit={(git.get('commit') or '?')[:12]} dirty={git.get('dirty')} "
            f"corpus={str(corpus.get('fingerprint') or '?')[:12]} top_k={info.get('top_k')}"
        )
    print(f"pairs={diff['pairs']} counts={diff['counts']}")
    print(f"unique changed chunks={diff['unique_changed_chunks']}")
    print(f"summary before={diff['summary_before']}")
    print(f"summary after ={diff['summary_after']}")
    print(
        f"ac05_violations={len(diff['ac05_violations'])} "
        f"order_changed_cases={len(diff['order_changed_cases'])} unmatched={len(diff['unmatched'])}"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chụp/so sánh locator citation trên golden set (RAG-22).")
    parser.add_argument("--dataset", type=Path, help="File dataset JSON.")
    parser.add_argument("--out", type=Path, help="File JSON kết quả (bản chụp hoặc diff).")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Số context mỗi câu (mặc định 10).")
    parser.add_argument("--embedding-cache", type=Path, default=DEFAULT_CACHE_FILE)
    parser.add_argument("--limit", type=int, help="Chỉ chạy N câu đầu (debug).")
    parser.add_argument("--diff", nargs=2, type=Path, metavar=("BEFORE.json", "AFTER.json"))
    args = parser.parse_args(argv)
    if args.diff is None and (args.dataset is None or args.out is None):
        parser.error("cần --dataset và --out (hoặc --diff BEFORE AFTER)")
    if not 1 <= args.top_k <= 20:
        parser.error("--top-k phải nằm trong 1..20")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.diff is not None:
        before, after = (json.loads(resolve_input(path).read_text(encoding="utf-8")) for path in args.diff)
        diff = diff_dumps(before, after)
        print_diff(diff)
        if args.out is not None:
            write_json(diff, resolve_output(args.out))
            print(f"\nDiff: {args.out}")
        return 0

    dump = dump_locators(resolve_input(args.dataset), args.top_k, args.embedding_cache, args.limit)
    output = resolve_output(args.out)
    write_json(dump, output)
    print(f"summary={dump['summary']}")
    print(f"corpus={dump['corpus']['fingerprint'][:16]} commit={(dump['git'].get('commit') or '?')[:12]}")
    print(f"Bản chụp: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean

from app.generation.rag_chain import RagChain, rag_chain
from scripts.eval_dataset import EvalCase, all_groups_rank, group_ranks, load_cases, slot_coverage


DEFAULT_DATASET = Path(__file__).parents[1] / "tests" / "fixtures" / "ptit_faq.json"


@dataclass(frozen=True)
class CaseResult:
    """Store retrieval and answer-quality metrics for one evaluation case."""

    id: str
    question: str
    retrieval_hit: bool
    reciprocal_rank: float
    answer_keyword_recall: float
    citation_validity: float
    answer_quality: float
    answer: str
    error: str | None = None


def load_faq_cases(path: Path) -> list[EvalCase]:
    """Load answerable cases whose evidence has keyword terms (schema v1 or v2).

    v1 `expected_terms` form a single evidence group, so a retrieval hit still means one
    context contains every term. v2 cases hit once the top-k covers every evidence group.
    Cases without terms (anchor-only or claim-only) would score a free keyword recall of 1.0,
    so they are left to `eval_retrieval` / `evaluate_ragas`.
    """

    dataset = load_cases(path, v1_evidence="single_group")
    cases = [case for case in dataset.cases if case.answerable and case.evidence and case.answer_slots]
    skipped = len(dataset.cases) - len(cases)
    if skipped:
        print(f"Skipped {skipped} cases without an answer or evidence terms.", file=sys.stderr)
    return cases


def _citation_validity(answer: str, sources: list[dict]) -> float:
    """Score 1 when the answer cites only source IDs returned by the RAG chain."""

    cited_ids = {int(value) for value in re.findall(r"\[(\d+)\]", answer)}
    valid_ids = {
        int(source["citation_id"])
        for source in sources
        if source.get("citation_id") is not None
    }
    return float(bool(cited_ids) and cited_ids <= valid_ids)


def evaluate_case(case: EvalCase, chain: RagChain, top_k: int) -> CaseResult:
    """Run one FAQ through the RAG chain and calculate its evaluation metrics."""

    question = case.query

    try:
        result = chain.answer(question, top_k=top_k)
    except Exception as exc:
        return CaseResult(
            id=case.id,
            question=question,
            retrieval_hit=False,
            reciprocal_rank=0.0,
            answer_keyword_recall=0.0,
            citation_validity=0.0,
            answer_quality=0.0,
            answer="",
            error=f"{type(exc).__name__}: {exc}",
        )

    contexts = result.get("contexts", [])
    answer = str(result.get("answer", ""))
    rank = all_groups_rank(group_ranks(contexts, case.evidence))
    keyword_recall = slot_coverage(answer, case.answer_slots)
    citation_validity = _citation_validity(answer, result.get("sources", []))

    return CaseResult(
        id=case.id,
        question=question,
        retrieval_hit=rank is not None,
        reciprocal_rank=1.0 / rank if rank else 0.0,
        answer_keyword_recall=keyword_recall,
        citation_validity=citation_validity,
        answer_quality=0.8 * keyword_recall + 0.2 * citation_validity,
        answer=answer,
    )


def evaluate(dataset: list[EvalCase], chain: RagChain, top_k: int) -> dict:
    """Evaluate all cases and return per-case results plus aggregate metrics."""

    results = [evaluate_case(case, chain, top_k) for case in dataset]
    count = len(results)
    summary = {
        "cases": count,
        "top_k": top_k,
        "retrieval_hit_rate": mean(item.retrieval_hit for item in results) if count else 0.0,
        "retrieval_mrr": mean(item.reciprocal_rank for item in results) if count else 0.0,
        "answer_keyword_recall": mean(item.answer_keyword_recall for item in results) if count else 0.0,
        "citation_validity": mean(item.citation_validity for item in results) if count else 0.0,
        "answer_quality": mean(item.answer_quality for item in results) if count else 0.0,
        "errors": sum(item.error is not None for item in results),
    }
    return {"summary": summary, "results": [asdict(item) for item in results]}


def _print_report(report: dict) -> None:
    """Print a compact human-readable evaluation report to standard output."""

    for item in report["results"]:
        status = "HIT" if item["retrieval_hit"] else "MISS"
        print(
            f"[{status}] {item['id']}: "
            f"RR={item['reciprocal_rank']:.2f} "
            f"Answer={item['answer_quality']:.2f}"
        )
        if item["error"]:
            print(f"  Error: {item['error']}")

    summary = report["summary"]
    print("\nSummary")
    print(f"  Retrieval Hit@{summary['top_k']}: {summary['retrieval_hit_rate']:.2%}")
    print(f"  Retrieval MRR:           {summary['retrieval_mrr']:.3f}")
    print(f"  Answer keyword recall:   {summary['answer_keyword_recall']:.2%}")
    print(f"  Citation validity:       {summary['citation_validity']:.2%}")
    print(f"  Answer quality:          {summary['answer_quality']:.2%}")
    print(f"  Errors:                  {summary['errors']}")


def _parse_args() -> argparse.Namespace:
    """Parse and validate command-line options for the evaluation run."""

    parser = argparse.ArgumentParser(
        description="Evaluate PTIT RAG retrieval hit rate and answer quality.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    parser.add_argument("--fail-below-hit-rate", type=float)
    parser.add_argument("--fail-below-answer-quality", type=float)
    args = parser.parse_args()
    if not 1 <= args.top_k <= 10:
        parser.error("--top-k must be between 1 and 10")
    for option in ("fail_below_hit_rate", "fail_below_answer_quality"):
        value = getattr(args, option)
        if value is not None and not 0.0 <= value <= 1.0:
            parser.error(f"--{option.replace('_', '-')} must be between 0 and 1")
    return args


def main() -> int:
    """Run evaluation, optionally write JSON, and enforce configured CI thresholds."""

    args = _parse_args()
    dataset = load_faq_cases(args.dataset)
    report = evaluate(dataset, rag_chain, args.top_k)
    _print_report(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nWrote JSON report to {args.output}")

    summary = report["summary"]
    if (
        args.fail_below_hit_rate is not None
        and summary["retrieval_hit_rate"] < args.fail_below_hit_rate
    ):
        return 1
    if (
        args.fail_below_answer_quality is not None
        and summary["answer_quality"] < args.fail_below_answer_quality
    ):
        return 1
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

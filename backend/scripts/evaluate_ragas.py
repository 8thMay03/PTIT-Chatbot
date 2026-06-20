from __future__ import annotations

import argparse
import asyncio
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from app.core.config import settings
from app.generation.rag_chain import RagChain, rag_chain


DEFAULT_DATASET = Path(__file__).parents[1] / "tests" / "fixtures" / "ptit_ragas_100.json"
METRIC_NAMES = ("context_precision", "faithfulness", "answer_correctness")


@dataclass(frozen=True)
class RagasCaseResult:
    """Store Ragas scores and generated content for one evaluation case."""

    id: str
    question: str
    response: str
    retrieved_contexts: list[str]
    reference: str
    scores: dict[str, float | None]
    errors: dict[str, str]


def build_sample(case: dict, chain: RagChain, top_k: int) -> dict:
    """Run one question through the application and build a Ragas-compatible sample."""

    reference = str(case.get("reference_answer", "")).strip()
    if not reference:
        raise ValueError(f"Case {case.get('id', '<unknown>')!r} has no reference_answer")

    result = chain.answer(str(case["question"]), top_k=top_k)
    return {
        "id": str(case["id"]),
        "user_input": str(case["question"]),
        "response": str(result.get("answer", "")),
        "retrieved_contexts": [
            str(context.get("text", ""))
            for context in result.get("contexts", [])
            if context.get("text")
        ],
        "reference": reference,
    }


def create_metrics(judge_model: str, api_key: str) -> dict[str, Any]:
    """Create modern Ragas metrics backed by one OpenAI judge model."""

    try:
        from openai import AsyncOpenAI
        from ragas.llms import llm_factory
        from ragas.metrics.collections import (
            AnswerCorrectness,
            ContextPrecision,
            Faithfulness,
        )
    except ImportError as exc:
        raise RuntimeError(
            'Ragas dependencies are missing or incompatible. '
            'Run: pip install -e ".[eval]"'
        ) from exc

    client = AsyncOpenAI(api_key=api_key)
    llm = llm_factory(judge_model, client=client)
    return {
        "context_precision": ContextPrecision(llm=llm),
        "faithfulness": Faithfulness(llm=llm),
        # Factual-only scoring avoids an additional embedding model and API call.
        "answer_correctness": AnswerCorrectness(
            llm=llm,
            weights=[1.0, 0.0],
        ),
    }


def _metric_inputs(metric_name: str, sample: dict) -> dict:
    """Select only the sample fields accepted by a specific Ragas metric."""

    common = {
        "user_input": sample["user_input"],
        "response": sample["response"],
    }
    if metric_name == "faithfulness":
        return {**common, "retrieved_contexts": sample["retrieved_contexts"]}
    if metric_name == "context_precision":
        return {
            "user_input": sample["user_input"],
            "reference": sample["reference"],
            "retrieved_contexts": sample["retrieved_contexts"],
        }
    if metric_name == "answer_correctness":
        return {**common, "reference": sample["reference"]}
    raise ValueError(f"Unsupported Ragas metric: {metric_name}")


async def score_sample(sample: dict, metrics: dict[str, Any]) -> RagasCaseResult:
    """Score one generated sample while isolating failures to individual metrics."""

    scores: dict[str, float | None] = {}
    errors: dict[str, str] = {}
    for name, metric in metrics.items():
        try:
            result = await metric.ascore(**_metric_inputs(name, sample))
            value = float(result.value)
            scores[name] = value if math.isfinite(value) else None
        except Exception as exc:
            scores[name] = None
            errors[name] = f"{type(exc).__name__}: {exc}"

    return RagasCaseResult(
        id=sample["id"],
        question=sample["user_input"],
        response=sample["response"],
        retrieved_contexts=sample["retrieved_contexts"],
        reference=sample["reference"],
        scores=scores,
        errors=errors,
    )


async def evaluate_ragas(
    dataset: list[dict],
    chain: RagChain,
    metrics: dict[str, Any],
    top_k: int,
) -> dict:
    """Generate answers, run all Ragas metrics, and aggregate valid scores."""

    results: list[RagasCaseResult] = []
    for case in dataset:
        try:
            sample = build_sample(case, chain, top_k)
            results.append(await score_sample(sample, metrics))
        except Exception as exc:
            results.append(
                RagasCaseResult(
                    id=str(case.get("id", "<unknown>")),
                    question=str(case.get("question", "")),
                    response="",
                    retrieved_contexts=[],
                    reference=str(case.get("reference_answer", "")),
                    scores={name: None for name in metrics},
                    errors={"pipeline": f"{type(exc).__name__}: {exc}"},
                )
            )

    summary: dict[str, Any] = {
        "cases": len(results),
        "top_k": top_k,
        "errors": sum(bool(item.errors) for item in results),
    }
    for name in metrics:
        valid_scores = [
            item.scores[name]
            for item in results
            if item.scores.get(name) is not None
        ]
        summary[name] = mean(valid_scores) if valid_scores else None

    available = [summary[name] for name in metrics if summary[name] is not None]
    summary["ragas_score"] = mean(available) if available else None
    return {"summary": summary, "results": [asdict(item) for item in results]}


def _print_report(report: dict) -> None:
    """Print per-case Ragas scores followed by aggregate metrics."""

    for item in report["results"]:
        rendered = " ".join(
            f"{name}={item['scores'].get(name):.3f}"
            if item["scores"].get(name) is not None
            else f"{name}=ERROR"
            for name in METRIC_NAMES
        )
        print(f"[{item['id']}] {rendered}")

    summary = report["summary"]
    print("\nSummary")
    for name in (*METRIC_NAMES, "ragas_score"):
        value = summary.get(name)
        print(f"  {name:20} {value:.3f}" if value is not None else f"  {name:20} N/A")
    print(f"  {'errors':20} {summary['errors']}")


def _parse_args() -> argparse.Namespace:
    """Parse CLI options and validate evaluation thresholds."""

    parser = argparse.ArgumentParser(description="Evaluate the PTIT RAG system with Ragas.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument(
        "--judge-model",
        default=settings.ragas_judge_model,
    )
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    parser.add_argument("--fail-below", type=float, help="Fail when ragas_score is below this value.")
    args = parser.parse_args()
    if not 1 <= args.top_k <= 10:
        parser.error("--top-k must be between 1 and 10")
    if args.fail_below is not None and not 0.0 <= args.fail_below <= 1.0:
        parser.error("--fail-below must be between 0 and 1")
    return args


def main() -> int:
    """Run the Ragas evaluation and optionally enforce a CI quality threshold."""

    args = _parse_args()
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is required for Ragas LLM-based metrics.")

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    metrics = create_metrics(args.judge_model, settings.openai_api_key)
    report = asyncio.run(evaluate_ragas(dataset, rag_chain, metrics, args.top_k))
    _print_report(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nWrote JSON report to {args.output}")

    score = report["summary"]["ragas_score"]
    if report["summary"]["errors"] or score is None:
        return 1
    if args.fail_below is not None and score < args.fail_below:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

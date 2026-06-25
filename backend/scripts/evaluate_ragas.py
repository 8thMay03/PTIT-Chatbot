from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from app.core.config import settings
from app.generation.rag_chain import RagChain, rag_chain


DEFAULT_DATASET = Path(__file__).parents[1] / "tests" / "fixtures" / "data.json"
DEFAULT_REPORT = Path(__file__).parents[1] / "report.json"
METRIC_NAMES = (
    "context_precision",
    "context_recall",
    "faithfulness",
    "answer_relevancy",
    "answer_correctness",
)


@dataclass(frozen=True)
class RagasCaseResult:
    """Store Ragas scores and generated content for one evaluation case."""

    id: str
    question: str
    response: str
    retrieved_contexts: list[str]
    reference: str
    reference_context: str
    question_type: str
    difficulty: str
    scores: dict[str, float | None]
    errors: dict[str, str]


class EvaluationProgress:
    """Render progress for pipeline generation and every Ragas metric."""

    def __init__(self, total_cases: int, metric_count: int) -> None:
        self.total_cases = total_cases
        self.steps_per_case = metric_count + 1
        self.total_steps = total_cases * self.steps_per_case
        self.completed_steps = 0
        self.started_at = time.monotonic()

    def show(self, case_number: int, case_id: str, stage: str) -> None:
        elapsed = time.monotonic() - self.started_at
        ratio = self.completed_steps / self.total_steps if self.total_steps else 1.0
        filled = round(24 * ratio)
        eta = (
            elapsed / self.completed_steps * (self.total_steps - self.completed_steps)
            if self.completed_steps
            else None
        )
        bar = "#" * filled + "-" * (24 - filled)
        eta_text = _format_duration(eta) if eta is not None else "--:--"
        print(
            f"\r[{bar}] {ratio:6.1%} case {case_number}/{self.total_cases} "
            f"{case_id[:28]:<28} {stage:<20} "
            f"elapsed {_format_duration(elapsed)} ETA {eta_text}",
            end="",
            file=sys.stderr,
            flush=True,
        )

    def advance(self, case_number: int, case_id: str, stage: str) -> None:
        self.completed_steps = min(self.total_steps, self.completed_steps + 1)
        self.show(case_number, case_id, stage)

    def skip_remaining_case_steps(self, case_number: int, case_id: str) -> None:
        self.completed_steps = max(self.completed_steps, case_number * self.steps_per_case)
        self.show(case_number, case_id, "pipeline error")

    def finish(self) -> None:
        if self.total_steps:
            self.completed_steps = self.total_steps
            self.show(self.total_cases, "complete", "done")
        print(file=sys.stderr, flush=True)


def _format_duration(seconds: float) -> str:
    seconds = max(0, round(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def normalize_case(case: dict, case_number: int | None = None) -> dict:
    """Normalize both the legacy fixture format and the Ragas dataset format."""

    user_input = str(case.get("user_input") or case.get("question") or "").strip()
    reference = str(case.get("reference") or case.get("reference_answer") or "").strip()
    case_id = str(case.get("id") or f"case_{case_number or 1:04d}")

    if not user_input:
        raise ValueError(f"Case {case_id!r} has no user_input")
    if not reference:
        raise ValueError(f"Case {case_id!r} has no reference")

    return {
        "id": case_id,
        "user_input": user_input,
        "reference": reference,
        "reference_context": str(case.get("reference_context", "")).strip(),
        "question_type": str(case.get("question_type", "")).strip(),
        "difficulty": str(case.get("difficulty", "")).strip(),
    }


def build_sample(
    case: dict,
    chain: RagChain,
    top_k: int,
    case_number: int | None = None,
) -> dict:
    """Run one question through the application and build a Ragas-compatible sample."""

    normalized = normalize_case(case, case_number)
    result = chain.answer(normalized["user_input"], top_k=top_k)
    return {
        **normalized,
        "response": str(result.get("answer", "")),
        "retrieved_contexts": [
            str(context.get("text", ""))
            for context in result.get("contexts", [])
            if context.get("text")
        ],
    }


def create_metrics(
    judge_model: str,
    embedding_model: str,
    api_key: str,
) -> dict[str, Any]:
    """Create modern Ragas metrics backed by one OpenAI judge model."""

    try:
        from openai import AsyncOpenAI
        from ragas.embeddings.base import embedding_factory
        from ragas.llms import llm_factory
        from ragas.metrics.collections import (
            AnswerCorrectness,
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            Faithfulness,
        )
    except ImportError as exc:
        raise RuntimeError(
            'Ragas dependencies are missing or incompatible. '
            'Run: pip install -e ".[eval]"'
        ) from exc

    client = AsyncOpenAI(api_key=api_key)
    llm = llm_factory(judge_model, client=client)
    embeddings = embedding_factory(
        "openai",
        model=embedding_model,
        client=client,
    )
    return {
        "context_precision": ContextPrecision(llm=llm),
        "context_recall": ContextRecall(llm=llm),
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=embeddings),
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
    if metric_name == "context_recall":
        return {
            "user_input": sample["user_input"],
            "reference": sample["reference"],
            "retrieved_contexts": sample["retrieved_contexts"],
        }
    if metric_name == "answer_relevancy":
        return common
    if metric_name == "answer_correctness":
        return {**common, "reference": sample["reference"]}
    raise ValueError(f"Unsupported Ragas metric: {metric_name}")


async def score_sample(
    sample: dict,
    metrics: dict[str, Any],
    progress_callback: Callable[[str, bool], None] | None = None,
) -> RagasCaseResult:
    """Score one generated sample while isolating failures to individual metrics."""

    scores: dict[str, float | None] = {}
    errors: dict[str, str] = {}
    for name, metric in metrics.items():
        if progress_callback:
            progress_callback(name, False)
        try:
            result = await metric.ascore(**_metric_inputs(name, sample))
            value = float(result.value)
            scores[name] = value if math.isfinite(value) else None
        except Exception as exc:
            scores[name] = None
            errors[name] = f"{type(exc).__name__}: {exc}"
        if progress_callback:
            progress_callback(name, True)

    return RagasCaseResult(
        id=sample["id"],
        question=sample["user_input"],
        response=sample["response"],
        retrieved_contexts=sample["retrieved_contexts"],
        reference=sample["reference"],
        reference_context=sample["reference_context"],
        question_type=sample["question_type"],
        difficulty=sample["difficulty"],
        scores=scores,
        errors=errors,
    )


async def evaluate_ragas(
    dataset: list[dict],
    chain: RagChain,
    metrics: dict[str, Any],
    top_k: int,
    show_progress: bool = False,
) -> dict:
    """Generate answers, run all Ragas metrics, and aggregate valid scores."""

    results: list[RagasCaseResult] = []
    progress = EvaluationProgress(len(dataset), len(metrics)) if show_progress else None
    for case_number, case in enumerate(dataset, start=1):
        case_id = str(case.get("id") or f"case_{case_number:04d}")
        try:
            if progress:
                progress.show(case_number, case_id, "pipeline")
            sample = build_sample(case, chain, top_k, case_number)
            if progress:
                progress.advance(case_number, case_id, "pipeline done")

            def update_progress(metric_name: str, completed: bool) -> None:
                if not progress:
                    return
                if completed:
                    progress.advance(case_number, case_id, f"{metric_name} done")
                else:
                    progress.show(case_number, case_id, metric_name)

            results.append(await score_sample(sample, metrics, update_progress))
        except Exception as exc:
            normalized = {
                "id": case_id,
                "user_input": str(case.get("user_input") or case.get("question") or ""),
                "reference": str(case.get("reference") or case.get("reference_answer") or ""),
                "reference_context": str(case.get("reference_context", "")),
                "question_type": str(case.get("question_type", "")),
                "difficulty": str(case.get("difficulty", "")),
            }
            results.append(
                RagasCaseResult(
                    id=normalized["id"],
                    question=normalized["user_input"],
                    response="",
                    retrieved_contexts=[],
                    reference=normalized["reference"],
                    reference_context=normalized["reference_context"],
                    question_type=normalized["question_type"],
                    difficulty=normalized["difficulty"],
                    scores={name: None for name in metrics},
                    errors={"pipeline": f"{type(exc).__name__}: {exc}"},
                )
            )
            if progress:
                progress.skip_remaining_case_steps(case_number, case_id)

    if progress:
        progress.finish()

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
    parser.add_argument(
        "--embedding-model",
        default=settings.ragas_embedding_model,
        help="OpenAI embedding model used by answer_relevancy.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"JSON report path (default: {DEFAULT_REPORT}).",
    )
    parser.add_argument("--fail-below", type=float, help="Fail when ragas_score is below this value.")
    parser.add_argument("--no-progress", action="store_true", help="Disable the progress bar.")
    args = parser.parse_args()
    if not 1 <= args.top_k <= 10:
        parser.error("--top-k must be between 1 and 10")
    if args.fail_below is not None and not 0.0 <= args.fail_below <= 1.0:
        parser.error("--fail-below must be between 0 and 1")
    return args


def load_dataset(path: Path) -> list[dict]:
    """Load a JSON array, a wrapped JSON object, or a Markdown JSON code block."""

    raw = path.read_text(encoding="utf-8").strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("```json")
        if start == -1:
            start = raw.find("```")
        if start == -1:
            raise ValueError(f"{path} is not valid JSON")
        start = raw.find("\n", start) + 1
        end = raw.find("```", start)
        if start == 0 or end == -1:
            raise ValueError(f"{path} contains an incomplete JSON code block")
        payload = json.loads(raw[start:end].strip())

    if isinstance(payload, dict):
        for key in ("data", "samples", "cases", "questions"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break

    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError(
            f"{path} must contain a JSON array of objects "
            "(or an object with data/samples/cases/questions)."
        )
    return payload


def main() -> int:
    """Run the Ragas evaluation and optionally enforce a CI quality threshold."""

    args = _parse_args()
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is required for Ragas LLM-based metrics.")

    dataset = load_dataset(args.dataset)
    metrics = create_metrics(
        args.judge_model,
        args.embedding_model,
        settings.openai_api_key,
    )
    report = asyncio.run(
        evaluate_ragas(
            dataset,
            rag_chain,
            metrics,
            args.top_k,
            show_progress=not args.no_progress,
        )
    )
    _print_report(report)

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

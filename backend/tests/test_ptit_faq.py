import json
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.ingestion.chunker import Chunk, split_text
from app.retrieval.bm25 import rank_bm25
from scripts.evaluate import _citation_validity, _evidence_rank, _term_coverage
from scripts.evaluate_ragas import _format_duration, build_sample, evaluate_ragas


FAQ_PATH = Path(__file__).parent / "fixtures" / "ptit_faq.json"
HANDBOOK_PATH = settings.documents_path / "so-tay-sinh-vien-d21.md"


def _load_faq_cases() -> list[dict]:
    return json.loads(FAQ_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def handbook_chunks() -> list[Chunk]:
    handbook = HANDBOOK_PATH.read_text(encoding="utf-8")
    return split_text(
        handbook,
        chunk_size=900,
        chunk_overlap=150,
    )


@pytest.mark.parametrize(
    "case",
    _load_faq_cases(),
    ids=lambda case: case["id"],
)
def test_common_ptit_question_retrieves_expected_evidence(
    case: dict,
    handbook_chunks: list[Chunk],
) -> None:
    """Keep common PTIT questions grounded in the checked-in student handbook."""
    ranked = rank_bm25(
        case["question"],
        [chunk.text for chunk in handbook_chunks],
        top_k=10,
    )
    retrieved_texts = [handbook_chunks[index].text.casefold() for index, _ in ranked]
    expected_terms = [term.casefold() for term in case["expected_terms"]]

    matching_text = next(
        (
            text
            for text in retrieved_texts
            if all(term in text for term in expected_terms)
        ),
        None,
    )

    assert matching_text is not None, (
        f"Không tìm thấy bằng chứng cho câu hỏi: {case['question']!r}. "
        f"Các cụm từ cần có trong cùng một chunk: {case['expected_terms']!r}"
    )


def test_evaluation_metrics_score_retrieval_answer_and_citations() -> None:
    contexts = [
        {"text": "Chuẩn đầu ra yêu cầu 450 điểm TOEIC."},
        {"text": "Nội dung không liên quan."},
    ]
    answer = "Sinh viên cần đạt 450 điểm TOEIC [1]."
    terms = ["450", "TOEIC"]

    assert _evidence_rank(contexts, terms) == 1
    assert _term_coverage(answer, terms) == 1.0
    assert _citation_validity(answer, [{"citation_id": 1}]) == 1.0
    assert _citation_validity(answer, [{"citation_id": 2}]) == 0.0


def test_all_faq_cases_have_reference_answers_for_ragas() -> None:
    assert all(case.get("reference_answer", "").strip() for case in _load_faq_cases())


def test_ragas_evaluator_builds_samples_and_aggregates_metrics() -> None:
    class FakeChain:
        def answer(self, question: str, top_k: int) -> dict:
            return {
                "answer": "Sinh viên cần đạt 450 điểm TOEIC [1].",
                "contexts": [{"text": "Chuẩn đầu ra yêu cầu 450 điểm TOEIC."}],
            }

    class FakeMetric:
        def __init__(self, value: float) -> None:
            self.value = value

        async def ascore(self, **kwargs) -> SimpleNamespace:
            assert kwargs
            return SimpleNamespace(value=self.value)

    case = {
        "id": "english_requirement",
        "question": "Chuẩn tiếng Anh là bao nhiêu?",
        "reference_answer": "Sinh viên cần đạt 450 điểm TOEIC.",
    }
    sample = build_sample(case, FakeChain(), top_k=4)

    assert sample["retrieved_contexts"] == ["Chuẩn đầu ra yêu cầu 450 điểm TOEIC."]

    report = asyncio.run(
        evaluate_ragas(
            [case],
            FakeChain(),
            {
                "context_precision": FakeMetric(0.8),
                "faithfulness": FakeMetric(0.9),
                "answer_correctness": FakeMetric(0.7),
            },
            top_k=4,
        )
    )

    assert report["summary"]["context_precision"] == pytest.approx(0.8)
    assert report["summary"]["faithfulness"] == pytest.approx(0.9)
    assert report["summary"]["answer_correctness"] == pytest.approx(0.7)
    assert report["summary"]["ragas_score"] == pytest.approx(0.8)
    assert report["summary"]["errors"] == 0


def test_ragas_progress_formats_duration() -> None:
    assert _format_duration(65) == "01:05"
    assert _format_duration(3661) == "01:01:01"

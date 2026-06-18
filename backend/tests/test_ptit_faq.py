import json
from pathlib import Path

import pytest

from app.core.config import settings
from app.ingestion.chunker import Chunk, split_text
from app.retrieval.bm25 import rank_bm25
from scripts.evaluate import _citation_validity, _evidence_rank, _term_coverage


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

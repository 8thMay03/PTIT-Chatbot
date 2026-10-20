import json
import asyncio
import unicodedata
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.ingestion.chunker import Chunk, split_text
from app.retrieval.bm25 import rank_bm25
from scripts.evaluate import _citation_validity, _evidence_rank, _term_coverage
from scripts.evaluate_ragas import _format_duration, build_sample, evaluate_ragas


FAQ_PATH = Path(__file__).parent / "fixtures" / "ptit_faq.json"
# Trích ngắn D26 đóng gói sẵn trong repo — đủ cho toàn bộ case FAQ.
HANDBOOK_EXCERPT_PATH = (
    Path(__file__).parent / "fixtures" / "corpus" / "so-tay-sinh-vien-d26-excerpt.md"
)


def _load_faq_cases() -> list[dict]:
    return json.loads(FAQ_PATH.read_text(encoding="utf-8"))


def _split_into_chunks(text: str) -> list[Chunk]:
    return split_text(
        unicodedata.normalize("NFC", text),
        chunk_size=900,
        chunk_overlap=150,
    )


def _corpus_markdown_files() -> list[Path]:
    root = Path(settings.documents_path)
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.is_file() and path.name != "test_chunker_tables _1_.md"
    )


def _assert_case_finds_expected_evidence(case: dict, chunks: list[Chunk]) -> None:
    ranked = rank_bm25(
        case["question"],
        [chunk.text for chunk in chunks],
        top_k=50,
    )
    retrieved_texts = [unicodedata.normalize("NFC", chunks[index].text).casefold() for index, _ in ranked]
    expected_terms = [unicodedata.normalize("NFC", term).casefold() for term in case["expected_terms"]]

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


@pytest.fixture(scope="module")
def handbook_chunks() -> list[Chunk]:
    handbook = HANDBOOK_EXCERPT_PATH.read_text(encoding="utf-8")
    return _split_into_chunks(handbook)


@pytest.fixture(scope="module")
def corpus_chunks() -> list[Chunk]:
    corpus_files = _corpus_markdown_files()
    if not corpus_files:
        pytest.skip(
            "Bỏ qua test kho tài liệu đầy đủ: không tìm thấy file .md nào trong "
            f"'{settings.documents_path}' (thư mục data/ bị gitignore, chỉ có trên "
            "máy có dữ liệu thật). Các case FAQ vẫn được kiểm tra trên trích ngắn "
            f"đóng gói sẵn tại '{HANDBOOK_EXCERPT_PATH}'."
        )
    corpus = "\n\n".join(path.read_text(encoding="utf-8") for path in corpus_files)
    return _split_into_chunks(corpus)


@pytest.mark.parametrize(
    "case",
    _load_faq_cases(),
    ids=lambda case: case["id"],
)
def test_common_ptit_question_retrieves_expected_evidence(
    case: dict,
    handbook_chunks: list[Chunk],
) -> None:
    """Keep common PTIT questions grounded in the checked-in D26 handbook excerpt."""
    _assert_case_finds_expected_evidence(case, handbook_chunks)


@pytest.mark.corpus
@pytest.mark.parametrize(
    "case",
    _load_faq_cases(),
    ids=lambda case: case["id"],
)
def test_common_ptit_question_retrieves_expected_evidence_from_full_corpus(
    case: dict,
    corpus_chunks: list[Chunk],
) -> None:
    """Full corpus must contain the evidence for every FAQ case.

    Không so top_k BM25 ở đây: trên kho đầy đủ, các đoạn cùng chủ đề (ví dụ
    "Giám đốc Học viện" của các đơn vị trực thuộc) có thể lấn át kết quả đúng
    trong top-50. Kiểm tra xếp hạng vẫn do test trên fixture đảm nhiệm.
    """
    expected_terms = [
        unicodedata.normalize("NFC", term).casefold()
        for term in case["expected_terms"]
    ]
    matching_text = next(
        (
            unicodedata.normalize("NFC", chunk.text).casefold()
            for chunk in corpus_chunks
            if all(term in unicodedata.normalize("NFC", chunk.text).casefold() for term in expected_terms)
        ),
        None,
    )

    assert matching_text is not None, (
        f"Kho tài liệu trong '{settings.documents_path}' không chứa bằng chứng cho "
        f"câu hỏi: {case['question']!r}. Các cụm từ cần có trong cùng một chunk: "
        f"{case['expected_terms']!r}"
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
                "context_recall": FakeMetric(0.6),
                "faithfulness": FakeMetric(0.9),
                "answer_relevancy": FakeMetric(1.0),
                "answer_correctness": FakeMetric(0.7),
            },
            top_k=4,
        )
    )

    assert report["summary"]["context_precision"] == pytest.approx(0.8)
    assert report["summary"]["context_recall"] == pytest.approx(0.6)
    assert report["summary"]["faithfulness"] == pytest.approx(0.9)
    assert report["summary"]["answer_relevancy"] == pytest.approx(1.0)
    assert report["summary"]["answer_correctness"] == pytest.approx(0.7)
    assert report["summary"]["ragas_score"] == pytest.approx(0.8)
    assert report["summary"]["errors"] == 0


def test_ragas_progress_formats_duration() -> None:
    assert _format_duration(65) == "01:05"
    assert _format_duration(3661) == "01:01:01"

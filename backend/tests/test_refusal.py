import pytest

from app.generation.llm import _normalize_answer_citations
from app.generation.refusal import NO_CONTEXT_ANSWER, is_refusal, normalize_refusal_text
from app.guardrails import OUT_OF_SCOPE_ANSWER


def _contexts() -> list[dict]:
    return [
        {"source_name": "handbook.md", "heading": "Học phí", "section_path": "Sổ tay > Học phí", "text": "A"},
        {"source_name": "handbook.md", "heading": "Học bổng", "section_path": "Sổ tay > Học bổng", "text": "B"},
    ]


REFUSAL_VARIANTS = [
    NO_CONTEXT_ANSWER,
    "Xin lỗi, chưa tìm thấy thông tin này trong tài liệu.",
    "Chưa tìm thấy thông tin này trong tài liệu được cung cấp.",
    "Xin lỗi, mình chưa tìm thấy thông tin này trong các tài liệu hiện có",
    "CHƯA TÌM THẤY THÔNG TIN NÀY TRONG TÀI LIỆU!",
    "**Chưa tìm thấy thông tin này trong tài liệu.**",
    "Chưa tìm thấy thông tin này trong tài liệu [1].",
    "Chưa tìm thấy thông tin này trong tài liệu. [2]",
    "Mình không tìm thấy thông tin này trong tài liệu.",
    "Chưa tìm thấy thông tin này trong tài liệu. Bạn có thể liên hệ Phòng Công tác sinh viên.",
    OUT_OF_SCOPE_ANSWER,
    "Xin lỗi, " + OUT_OF_SCOPE_ANSWER[0].lower() + OUT_OF_SCOPE_ANSWER[1:],
    "Mình chỉ hỗ trợ các câu hỏi liên quan đến PTIT thôi nhé [1].",
]


@pytest.mark.parametrize("answer", REFUSAL_VARIANTS)
def test_refusal_variants_lose_citations_and_are_recognized(answer: str) -> None:
    normalized = _normalize_answer_citations(answer, _contexts())

    assert is_refusal(answer, {1, 2})
    assert "[" not in normalized
    assert is_refusal(normalized)


def test_exact_refusals_are_returned_unchanged() -> None:
    assert _normalize_answer_citations(NO_CONTEXT_ANSWER, _contexts()) == NO_CONTEXT_ANSWER
    assert _normalize_answer_citations(OUT_OF_SCOPE_ANSWER, _contexts()) == OUT_OF_SCOPE_ANSWER
    assert (
        _normalize_answer_citations("Chưa tìm thấy thông tin này trong tài liệu [1].", _contexts())
        == NO_CONTEXT_ANSWER
    )


def test_partial_answer_with_valid_citation_after_refusal_phrase_is_not_refusal() -> None:
    answer = "Chưa tìm thấy thông tin này trong tài liệu. Tuy nhiên, học phí được đóng theo học kỳ [1]."

    assert not is_refusal(answer, {1, 2})
    assert _normalize_answer_citations(answer, _contexts()) == answer


def test_invalid_citation_after_refusal_phrase_does_not_make_partial_answer() -> None:
    answer = "Chưa tìm thấy thông tin này trong tài liệu. Xem thêm [7]."

    assert is_refusal(answer, {1, 2})
    assert _normalize_answer_citations(answer, _contexts()) == (
        "Chưa tìm thấy thông tin này trong tài liệu. Xem thêm."
    )


@pytest.mark.parametrize(
    "answer",
    [
        "Học phí được đóng theo học kỳ [1].",
        "Tài liệu chưa đề cập mức phạt cụ thể.",
        "Học phí đóng theo học kỳ [1]. Tài liệu chưa tìm thấy thông tin này về miễn giảm.",
        "",
    ],
)
def test_non_refusal_answers(answer: str) -> None:
    assert not is_refusal(answer)


def test_normalize_refusal_text() -> None:
    assert normalize_refusal_text("**Chưa  tìm thấy** [1] thông tin.") == "chưa tìm thấy thông tin"

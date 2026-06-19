from app.generation.llm import _extractive_answer, _normalize_answer_citations
from app.generation.prompts import SYSTEM_PROMPT, build_context_prompt


def _contexts() -> list[dict]:
    return [
        {
            "source": "C:\\private\\data\\handbook.md",
            "source_name": "handbook.md",
            "heading": "Tuition",
            "section_path": "Handbook > Tuition",
            "text": "Tuition policy content.",
        },
        {
            "source": "C:\\private\\data\\handbook.md",
            "source_name": "handbook.md",
            "heading": "Tuition",
            "section_path": "Handbook > Tuition",
            "text": "More tuition details.",
        },
    ]


def test_prompt_uses_clean_deduplicated_citation_numbers() -> None:
    prompt = build_context_prompt("Học phí thế nào?", _contexts())

    assert prompt.count("[1] Nguồn: handbook.md") == 2
    assert "[2]" not in prompt
    assert "C:\\private" not in prompt
    assert "Mỗi nhận định thực tế" in SYSTEM_PROMPT


def test_extractive_answer_includes_citations() -> None:
    answer = _extractive_answer(_contexts())

    assert answer.count("[1]") == 2


def test_answer_citations_are_limited_to_provided_sources() -> None:
    answer = _normalize_answer_citations("Thông tin học phí [9].", _contexts())

    assert "[9]" not in answer
    assert answer.endswith("[1]")


def test_prompt_separates_conversation_memory_from_document_context() -> None:
    history = [{"role": "user", "content": "Câu hỏi trước về học phí"}]

    prompt = build_context_prompt("Còn thời hạn?", _contexts(), history)

    assert "LỊCH SỬ HỘI THOẠI (chỉ để hiểu tham chiếu)" in prompt
    assert "Người dùng: Câu hỏi trước về học phí" in prompt
    assert "NGỮ CẢNH TÀI LIỆU ĐƯỢC PHÉP SỬ DỤNG" in prompt

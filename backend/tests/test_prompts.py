from app.generation.llm import _extractive_answer, _normalize_answer_citations
from app.guardrails import OUT_OF_SCOPE_ANSWER
from app.generation.prompts import SYSTEM_PROMPT, build_context_prompt
from app.generation.refusal import NO_CONTEXT_ANSWER


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
    assert "Vị trí trích dẫn: Tuition" in prompt


def test_extractive_answer_includes_citations() -> None:
    answer = _extractive_answer(_contexts())

    assert answer.count("[1]") == 2


def test_answer_citations_are_limited_to_provided_sources() -> None:
    answer = _normalize_answer_citations("Thông tin học phí [9].", _contexts())

    # RAG-22: bỏ số citation bịa, không tự gắn [1] thay thế.
    assert answer == "Thông tin học phí."


def test_valid_citations_are_kept_and_none_are_added() -> None:
    assert _normalize_answer_citations("Học phí [1] và lệ phí [3].", _contexts()) == "Học phí [1] và lệ phí."
    partial = "Học phí đóng theo kỳ. Tài liệu chưa đề cập mức phạt khi đóng trễ."
    assert _normalize_answer_citations(partial, _contexts()) == partial


def test_context_prompt_states_both_refusal_sentences() -> None:
    prompt = build_context_prompt("Học phí thế nào?", _contexts())

    assert f"thông tin để trả lời: {NO_CONTEXT_ANSWER}" in prompt
    assert f"Câu từ chối ngoài phạm vi: {OUT_OF_SCOPE_ANSWER}" in prompt


def test_prompt_separates_conversation_memory_from_document_context() -> None:
    history = [{"role": "user", "content": "Câu hỏi trước về học phí"}]

    prompt = build_context_prompt("Còn thời hạn?", _contexts(), history)

    assert "LỊCH SỬ HỘI THOẠI (chỉ để hiểu tham chiếu)" in prompt
    assert "Người dùng: Câu hỏi trước về học phí" in prompt
    assert "NGỮ CẢNH TÀI LIỆU ĐƯỢC PHÉP SỬ DỤNG" in prompt


def test_system_prompt_enforces_ptit_scope_and_blocks_code_generation() -> None:
    assert "Phạm vi duy nhất" in SYSTEM_PROMPT
    assert "Không viết mã nguồn" in SYSTEM_PROMPT


def test_system_prompt_prioritizes_relevant_and_complete_answers() -> None:
    assert "Đưa câu trả lời chính ngay ở câu đầu tiên" in SYSTEM_PROMPT
    assert "Loại bỏ mọi câu không trực tiếp giúp trả lời câu hỏi" in SYSTEM_PROMPT
    assert "Kiểm tra câu trả lời cuối cùng đã trả lời đủ từng ý" in SYSTEM_PROMPT
    assert "không tóm tắt toàn bộ ngữ cảnh" in SYSTEM_PROMPT


def test_out_of_scope_refusal_does_not_receive_a_citation() -> None:
    assert _normalize_answer_citations(OUT_OF_SCOPE_ANSWER, _contexts()) == OUT_OF_SCOPE_ANSWER

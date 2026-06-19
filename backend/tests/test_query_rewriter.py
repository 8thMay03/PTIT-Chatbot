from app.generation.query_rewriter import VietnameseQueryRewriter, rule_based_rewrite


def test_rule_based_rewrite_removes_filler_and_expands_vietnamese_abbreviations() -> None:
    rewritten = rule_based_rewrite("Cho mình hỏi SV đăng ký ĐKHP ở đâu ạ?")

    assert rewritten == "sinh viên đăng ký học phần ở đâu"


def test_rule_based_rewrite_preserves_codes_and_numbers() -> None:
    rewritten = rule_based_rewrite("Xin hỏi GPA môn INT123 năm 2025 là bao nhiêu?")

    assert "điểm trung bình gpa" in rewritten
    assert "int123" in rewritten
    assert "2025" in rewritten


def test_rewriter_resolves_vietnamese_follow_up_from_recent_history(monkeypatch) -> None:
    monkeypatch.setattr("app.generation.query_rewriter.settings.query_rewrite_use_llm", False)
    history = [
        {"role": "user", "content": "Điều kiện cảnh báo học tập là gì?"},
        {"role": "assistant", "content": "Thông tin trả lời trước."},
    ]

    rewritten = VietnameseQueryRewriter().rewrite("Còn trường hợp đó thì sao?", history)

    assert rewritten.startswith("điều kiện cảnh báo học tập")
    assert "còn trường hợp đó thì sao" in rewritten

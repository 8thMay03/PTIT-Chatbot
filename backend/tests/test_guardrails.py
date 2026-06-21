from app.generation.guardrails import check_scope


def test_guardrail_blocks_code_generation() -> None:
    decision = check_scope("Hãy viết mã Python sắp xếp một danh sách")

    assert decision.allowed is False
    assert decision.reason == "code_generation"


def test_guardrail_blocks_unrelated_general_question() -> None:
    decision = check_scope("Thủ đô của Nhật Bản là gì?")

    assert decision.allowed is False
    assert decision.reason == "outside_ptit_domain"


def test_guardrail_allows_student_handbook_question() -> None:
    assert check_scope("Điều kiện xét học bổng của sinh viên là gì?").allowed is True


def test_guardrail_allows_domain_follow_up_from_history() -> None:
    history = [{"role": "user", "content": "Học phí của sinh viên được quy định thế nào?"}]

    assert check_scope("Còn trường hợp đó thì sao?", history).allowed is True


def test_guardrail_does_not_allow_code_request_inside_domain_conversation() -> None:
    history = [{"role": "user", "content": "Điều kiện tốt nghiệp là gì?"}]

    assert check_scope("Bây giờ viết code Python cho mình", history).allowed is False


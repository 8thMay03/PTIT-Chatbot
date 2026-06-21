from app.generation.citations import numbered_contexts, public_citations


def test_citation_extracts_article_clause_and_point() -> None:
    contexts = [{
        "source_name": "so-tay.md",
        "heading": "Điều 33. Cảnh báo kết quả học tập",
        "section_path": "Quy chế đào tạo > Điều 33. Cảnh báo kết quả học tập",
        "text": "## Điều 33. Cảnh báo kết quả học tập\n\n2. Sinh viên bị cảnh báo khi:\n\na) Điểm quá thấp.",
    }]

    citation = public_citations(contexts)[0]

    assert citation["article"] == "Điều 33. Cảnh báo kết quả học tập"
    assert citation["clauses"] == ["2"]
    assert citation["points"] == ["a"]
    assert citation["locator"] == "Điều 33. Cảnh báo kết quả học tập — Khoản 2; Điểm a"


def test_chunks_from_different_clauses_receive_different_citation_numbers() -> None:
    base = {
        "source_name": "so-tay.md",
        "heading": "Điều 12. Thu học phí",
        "section_path": "Quy định học phí > Điều 12. Thu học phí",
    }
    contexts = [
        {**base, "text": "1. Học phí được thu hàng tháng."},
        {**base, "text": "2. Thời hạn thu do cơ sở đào tạo quy định."},
    ]

    assert [number for number, _ in numbered_contexts(contexts)] == [1, 2]


def test_citation_falls_back_to_heading_when_no_legal_locator_exists() -> None:
    citation = public_citations([{
        "source_name": "so-tay.md",
        "heading": "Lịch tiếp sinh viên",
        "section_path": "Thủ tục hành chính > Lịch tiếp sinh viên",
        "text": "Sinh viên liên hệ trong giờ hành chính.",
    }])[0]

    assert citation["article"] is None
    assert citation["locator"] == "Lịch tiếp sinh viên"

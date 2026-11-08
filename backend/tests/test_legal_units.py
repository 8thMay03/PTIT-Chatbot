from app.ingestion.legal_units import extract_article, extract_legal_units


def test_numbered_lists_outside_an_article_are_not_clauses() -> None:
    units = extract_legal_units(
        "Thủ tục cấp giấy xác nhận",
        "Sổ tay > Thủ tục > Thủ tục cấp giấy xác nhận",
        "## Thủ tục cấp giấy xác nhận\n\n1. Nộp đơn tại một cửa.\n2) Nhận phiếu hẹn.\n\na) Bản sao CCCD.\nb. Ảnh thẻ.",
        open_clause="3",
    )

    assert units.article is None
    assert units.clauses == []
    assert units.points == []
    assert units.last_clause is None


def test_article_from_heading_collects_clauses_and_points() -> None:
    units = extract_legal_units(
        "Điều 33. Cảnh báo kết quả học tập",
        "Quy chế > Điều 33. Cảnh báo kết quả học tập",
        "## Điều 33. Cảnh báo kết quả học tập\n\n1. Cảnh báo theo học kỳ.\n\n2. Sinh viên bị cảnh báo khi:\n\na) Điểm thấp;\n- b) Nợ tín chỉ.",
    )

    assert units.article == "Điều 33. Cảnh báo kết quả học tập"
    assert units.clauses == ["1", "2"]
    assert units.points == ["a", "b"]
    assert units.last_clause == "2"


def test_article_from_section_path_only() -> None:
    units = extract_legal_units(
        "Học phí",
        "Quy định > Điều 12. Thu học phí > Học phí",
        "1. Học phí thu theo học kỳ.",
    )

    assert units.article == "Điều 12. Thu học phí"
    assert units.clauses == ["1"]


def test_article_from_bold_line_at_top_of_text() -> None:
    # LlamaParse hay để "Điều N" dạng chữ đậm, không phải heading markdown.
    units = extract_legal_units(
        "Chương II",
        "Quy chế > Chương II",
        "**Điều 7. Chuẩn đầu ra**\n\n1. Kiến thức.\n\n2. Kỹ năng.",
    )

    assert units.article == "Điều 7. Chuẩn đầu ra"
    assert units.clauses == ["1", "2"]


def test_parenthesised_numbers_are_not_clauses_even_inside_an_article() -> None:
    units = extract_legal_units("Điều 5. Hồ sơ", "Điều 5. Hồ sơ", "1) Đơn.\n2) Ảnh.")

    assert units.article == "Điều 5. Hồ sơ"
    assert units.clauses == []


def test_numbered_lines_inside_tables_are_not_clauses() -> None:
    text = (
        "## Điều 9. Mức thu\n\n"
        "| STT | Nội dung |\n| --- | --- |\n| 1. | Học phí |\n"
        "<table>\n<tr><td>\n2. Lệ phí\n</td></tr>\n</table>\n\n"
        "3. Mức thu điều chỉnh hằng năm."
    )

    units = extract_legal_units("Điều 9. Mức thu", "Điều 9. Mức thu", text)

    assert units.clauses == ["3"]


def test_chunk_starting_mid_clause_inherits_open_clause() -> None:
    units = extract_legal_units(
        "Điều 33. Cảnh báo",
        "Điều 33. Cảnh báo",
        "## Điều 33. Cảnh báo\n\nc) Không đóng học phí;\n\nd) Vi phạm quy chế.\n\n3. Mức cảnh báo.",
        open_clause="2",
    )

    assert units.clauses == ["2", "3"]
    assert units.points == ["c", "d"]
    assert units.last_clause == "3"


def test_continuation_without_markers_keeps_open_clause() -> None:
    units = extract_legal_units(
        "Điều 33. Cảnh báo", "Điều 33. Cảnh báo", "## Điều 33. Cảnh báo\n\nvà các trường hợp khác.", open_clause="2"
    )

    assert units.clauses == ["2"]
    assert units.last_clause == "2"


def test_open_clause_is_not_inherited_when_text_starts_with_a_clause() -> None:
    units = extract_legal_units("Điều 33", "Điều 33", "3. Mức cảnh báo.\n\na) Mức 1.", open_clause="2")

    assert units.clauses == ["3"]
    assert units.points == ["a"]


def test_new_article_in_body_closes_open_clause() -> None:
    units = extract_legal_units(
        "Chương III",
        "Quy chế > Chương III",
        "**Điều 7. Chuẩn đầu ra**\n\na) Kiến thức.\n\n**Điều 8. Khối lượng**\n\nb) Tín chỉ.",
        open_clause="4",
    )

    assert units.article == "Điều 7. Chuẩn đầu ra"
    assert units.clauses == []
    assert units.points == ["a", "b"]
    assert units.last_clause is None


def test_units_are_capped() -> None:
    text = "\n".join(f"{number}. Nội dung." for number in range(1, 20))

    assert len(extract_legal_units("Điều 1", "", text).clauses) == 12


def test_extract_article_scans_only_first_lines() -> None:
    text = "\n".join(["Dòng."] * 8 + ["Điều 9. Muộn"])

    assert extract_article("", "", text) is None


def test_inline_clause_continues_open_clause_sequence() -> None:
    # Bản LlamaParse hay gộp các Khoản vào một đoạn.
    units = extract_legal_units(
        "Điều 16. Đồ án",
        "Điều 16. Đồ án",
        "## Điều 16. Đồ án\n\nphải tự chịu trách nhiệm khi bảo vệ. 5. Hai tuần trước khi bảo vệ, sinh viên nộp.",
        open_clause="4",
    )

    assert units.clauses == ["4", "5"]
    assert units.last_clause == "5"


def test_inline_clauses_after_a_line_start_clause() -> None:
    units = extract_legal_units("Điều 6", "Điều 6", "1. Chương trình đào tạo. 2. Chương trình thể hiện rõ; 3. Đề cương.")

    assert units.clauses == ["1", "2", "3"]
    assert units.last_clause == "3"


def test_out_of_sequence_inline_number_drops_open_clause() -> None:
    units = extract_legal_units(
        "Điều 6", "Điều 6", "đủ điều kiện xét. 7. Sinh viên đạt yêu cầu khi đủ điểm.", open_clause="2"
    )

    # Nội dung đầu vẫn thuộc Khoản 2, nhưng sau "7." không còn chắc Khoản nào đang mở.
    assert units.clauses == ["2"]
    assert units.last_clause is None
    # "điểm 10." không đứng sau dấu kết câu nên không phải dấu Khoản.
    assert extract_legal_units("Điều 6", "", "theo thang điểm 10. Sinh viên.", open_clause="2").last_clause == "2"


def test_inline_number_followed_by_lowercase_is_not_a_clause() -> None:
    units = extract_legal_units("Điều 6", "Điều 6", "1. Mức điểm tối thiểu là 5. và các trường hợp khác.")

    assert units.clauses == ["1"]
    assert units.last_clause == "1"


def test_continuation_before_line_start_clause_inherits_open_clause() -> None:
    units = extract_legal_units(
        "Điều 6", "Điều 6", "tiếp nối nội dung Khoản trước.\n\n3. Khoản kế tiếp.", open_clause="2"
    )

    assert units.clauses == ["2", "3"]


def test_restarted_numbering_does_not_inherit_open_clause() -> None:
    # Dòng tiêu đề không phải heading rồi đánh số lại từ 1: không phải phần tiếp của Khoản 4.
    units = extract_legal_units(
        "Điều 5",
        "Điều 5",
        "Điều kiện hoàn thành chương trình đào tạo\n1. Chương trình có nhiều PLO.\n2. Mỗi PLO được đo.",
        open_clause="4",
    )

    assert units.clauses == ["1", "2"]
    assert units.last_clause == "2"

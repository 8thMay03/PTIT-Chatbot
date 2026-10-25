import re
from pathlib import Path

import pytest

from app.ingestion.chunker import split_text
from app.parsers.normalize import classify_heading, normalize_markdown

FIXTURES = Path(__file__).parent / "fixtures" / "corpus" / "heading-normalization"
BOLD_MD = FIXTURES / "bold-md.md"
DOCLING_FLAT = FIXTURES / "docling-flat.md"

PART_IV = "PHẦN IV: MỘT SỐ QUY CHẾ, QUY ĐỊNH VỀ QUẢN LÝ ĐÀO TẠO"
TRAINING_RULES = "QUY ĐỊNH ĐÀO TẠO ĐẠI HỌC THEO TÍN CHỈ CỦA HỌC VIỆN"
EXAM_RULES = "QUY ĐỊNH TỔ CHỨC THI KẾT THÚC HỌC PHẦN, THI HỌC PHẦN THAY THẾ TỐT NGHIỆP TRÌNH ĐỘ ĐẠI HỌC CỦA HỌC VIỆN"
IT_PROGRAM = "KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN NGÀNH CÔNG NGHỆ THÔNG TIN KHÓA 2026"

EXPECTED_TREE = [
    (1, "MỤC LỤC"),
    (1, "LỜI NÓI ĐẦU"),
    (1, "PHẦN III: CHƯƠNG TRÌNH VÀ KẾ HOẠCH ĐÀO TẠO"),
    (2, IT_PROGRAM),
    (4, "NĂM HỌC THỨ NHẤT"),
    (3, "CHUYỂN NGÀNH HỆ THÔNG THÔNG TIN"),
    (4, "NĂM THỨ NĂM"),
    (5, "(*): Các học phần tự chọn"),
    (1, PART_IV),
    (2, TRAINING_RULES),
    (3, "Chương I: NHỮNG QUY ĐỊNH CHUNG"),
    (5, "Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng"),
    (3, "Chương II: CHƯƠNG TRÌNH ĐÀO TẠO"),
    (5, "Điều 5. Ngành đào tạo"),
    (3, "Chương III: TỔ CHỨC ĐÀO TẠO"),
    (5, "Điều 8. Thời gian và kế hoạch đào tạo"),
    (6, "1. Thời gian của khóa học"),
    (6, "2. Khóa học"),
    (5, "Điều 9. Đăng ký nhập học"),
    (5, "Điều 10. Tổ chức lớp học"),
    (3, "Chương V: ĐÁNH GIÁ KẾT QUẢ VÀ THI KẾT THÚC HỌC PHẦN"),
    (5, "Điều 23. Tiêu chí đánh giá kết quả học tập"),
    (3, "Chương VI: XỬ LÝ HỌC TẬP"),
    (5, "Điều 33. Cảnh báo kết quả học tập"),
    (2, EXAM_RULES),
    (3, "Chương III: ĐIỀU KIỆN DỰ THI"),
    (5, "Điều 8. Xác định điều kiện thi"),
    (3, "Chương VII: XỬ LÝ VI PHẠM"),
    (5, "Điều 28. Nguyên tắc chung"),
    (1, "PHẦN V: MỘT SỐ QUY CHẾ, QUY ĐỊNH, QUY TRÌNH VỀ CÔNG TÁC SINH VIÊN, HỖ TRỢ SINH VIÊN"),
    (2, "QUY ĐỊNH CÔNG TÁC SINH VIÊN TRÌNH ĐỘ ĐẠI HỌC CHÍNH QUY"),
    (3, "Chương I: NHỮNG QUY ĐỊNH CHUNG"),
    (5, "Điều 1. Phạm vi Điều chỉnh và đối tượng áp dụng"),
    (3, "Chương VI: HỆ THỐNG TỔ CHỨC, QUẢN LÝ"),
    (5, "Điều 22. Lớp sinh viên"),
    (2, "LỊCH TIẾP SINH VIÊN CỦA PHÒNG/TRUNG TÂM CHỨC NĂNG"),
]

_HEADING = re.compile(r"^(#{1,6}) (.+)$")


def _tree(markdown: str) -> list[tuple[int, str]]:
    return [
        (len(match.group(1)), match.group(2))
        for line in markdown.splitlines()
        if (match := _HEADING.match(line))
    ]


def _normalized(path: Path) -> str:
    return normalize_markdown(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("fixture", [BOLD_MD, DOCLING_FLAT], ids=["bold-md", "docling-flat"])
def test_both_input_styles_produce_the_expected_heading_tree(fixture):
    assert _tree(_normalized(fixture)) == EXPECTED_TREE


@pytest.mark.parametrize("fixture", [BOLD_MD, DOCLING_FLAT], ids=["bold-md", "docling-flat"])
def test_normalization_is_idempotent(fixture):
    once = _normalized(fixture)

    assert normalize_markdown(once) == once


@pytest.mark.parametrize("fixture", [BOLD_MD, DOCLING_FLAT], ids=["bold-md", "docling-flat"])
def test_article_section_path_names_regulation_and_chapter(fixture):
    chunks = split_text(_normalized(fixture), chunk_size=2048, chunk_overlap=0)
    paths = {chunk.heading: chunk.section_path for chunk in chunks}

    assert paths["Điều 33. Cảnh báo kết quả học tập"] == (
        f"{PART_IV} > {TRAINING_RULES} > Chương VI: XỬ LÝ HỌC TẬP > Điều 33. Cảnh báo kết quả học tập"
    )
    # Two regulations share "Điều 8."; the path tells them apart.
    assert paths["Điều 8. Xác định điều kiện thi"].startswith(f"{PART_IV} > {EXAM_RULES} > Chương III")
    assert paths["2. Khóa học"].endswith("Chương III: TỔ CHỨC ĐÀO TẠO > Điều 8. Thời gian và kế hoạch đào tạo > 2. Khóa học")


@pytest.mark.parametrize("fixture", [BOLD_MD, DOCLING_FLAT], ids=["bold-md", "docling-flat"])
def test_no_chunk_spans_two_articles(fixture):
    for chunk in split_text(_normalized(fixture), chunk_size=2048, chunk_overlap=0):
        assert len(re.findall(r"(?m)^#{1,6} Điều \d+", chunk.text)) <= 1, chunk.text


@pytest.mark.parametrize("fixture", [BOLD_MD, DOCLING_FLAT], ids=["bold-md", "docling-flat"])
def test_study_plan_chunks_carry_the_program_name(fixture):
    chunks = split_text(_normalized(fixture), chunk_size=2048, chunk_overlap=0)
    plan_chunks = [chunk for chunk in chunks if "NĂM" in chunk.section_path or "tự chọn" in chunk.section_path]

    assert plan_chunks
    assert all(chunk.section_path.startswith(f"PHẦN III: CHƯƠNG TRÌNH VÀ KẾ HOẠCH ĐÀO TẠO > {IT_PROGRAM}") for chunk in plan_chunks)


def test_escapes_and_unicode_are_normalized():
    text = normalize_markdown("Phòng CT&amp;CTSV, mã 7480201\\_VNH, Điều")

    assert text == "Phòng CT&CTSV, mã 7480201_VNH, Điều"


def test_plain_text_without_structure_is_unchanged():
    text = "Legacy caller\n\nMột đoạn văn bình thường.\n"

    assert normalize_markdown(text) == text


def test_table_of_contents_entries_do_not_become_headings():
    text = normalize_markdown("# MỤC LỤC\n\n## **PHẦN I: TỔNG QUAN** **5**\n\n**PHẦN IV: QUY CHẾ** 120\n\n# LỜI NÓI ĐẦU\n")

    assert _tree(text) == [(1, "MỤC LỤC"), (1, "LỜI NÓI ĐẦU")]
    assert "**PHẦN I: TỔNG QUAN** **5**" in text


@pytest.mark.parametrize(
    "line",
    [
        "**129**",
        "**1. Mức vay vốn tối đa là 4.000.000 đồng/tháng/học sinh, sinh viên.**",
        "Chương II của Quy định này áp dụng cho mọi sinh viên",
        "Chương trình Công nghệ thông tin Việt Nhật (mã ngành XT: 7480201_VNH)",
        "- Điều 5. Không phải heading vì là mục danh sách",
    ],
)
def test_non_headings_are_not_promoted(line):
    assert _tree(normalize_markdown(f"Đoạn trước.\n\n{line}\n\nĐoạn sau.")) == []


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Điều 10. Đánh giá kết quả thực tập tốt nghiệp", (5, "Điều 10. Đánh giá kết quả thực tập tốt nghiệp")),
        ("**ĐIỀU 8. TỔ CHỨC THỰC TẬP**", (5, "ĐIỀU 8. TỔ CHỨC THỰC TẬP")),
        ("**Điều 13: Quy trình đánh giá:**", (5, "Điều 13: Quy trình đánh giá")),
        ("…Điều 2. Đối tượng được vay vốn:", (5, "Điều 2. Đối tượng được vay vốn")),
        ("Chương IV KHEN THƯỞNG", (3, "Chương IV: KHEN THƯỞNG")),
        ("Mục 2 QUY TRÌNH THỦ TỤC", (4, "Mục 2: QUY TRÌNH THỦ TỤC")),
        ("II/ Quyết định số 05/2022/QĐ-TTg về tín dụng đối với học sinh, sinh viên", (2, "II/ Quyết định số 05/2022/QĐ-TTg về tín dụng đối với học sinh, sinh viên")),
        ("PHỤ LỤC 2: BẢNG QUY ĐỔI", (2, "PHỤ LỤC 2: BẢNG QUY ĐỔI")),
    ],
)
def test_structural_lines_are_promoted(line, expected):
    assert _tree(normalize_markdown(f"Đoạn trước.\n\n{line}\n\nĐoạn sau.")) == [expected]


def test_bold_label_with_colon_nests_under_previous_heading():
    text = normalize_markdown("# V. PHÒNG TÀI CHÍNH KẾ TOÁN\n\n**Lãnh đạo phòng:**\n\nTrưởng phòng\n\n**Thông Báo**\n")

    assert _tree(text) == [(1, "V. PHÒNG TÀI CHÍNH KẾ TOÁN"), (2, "Lãnh đạo phòng"), (2, "Thông Báo")]


def test_year_headings_outside_a_study_plan_are_not_structural():
    assert classify_heading("Học kỳ ......Năm học........") == "other"
    assert classify_heading("NĂM HỌC THỨ NHẤT", in_program=True) == "year"
    assert classify_heading("CHUYẾN NGÀNH CÔNG NGHỆ PHẦN MỀM", in_program=True) == "major"


def test_lines_inside_tables_and_code_are_left_alone():
    text = (
        "<table>\n<tr><td>\n**Điều 5. Trong bảng**\n</td></tr>\n</table>\n\n"
        "| **Điều 6. Ô bảng** |\n|---|\n\n"
        "```\n**Điều 7. Trong code**\n```\n"
    )

    assert normalize_markdown(text) == text

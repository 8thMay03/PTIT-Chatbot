"""Task table-search-context: tuần tự hóa hàng bảng "Cột: giá trị" cho search_text."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import settings
from app.ingestion.chunker import (
    _table_cells_safe,
    serialize_table_row,
    split_parent_child,
    table_row_search_index,
    table_search_body,
)
from app.ingestion.cleaner import clean_text


def _serialize(header: str, row: str, prev: list[str] | None = None) -> tuple[str, list[str]]:
    return serialize_table_row(_table_cells_safe(header), _table_cells_safe(row), prev or [])


def test_full_row_is_serialized_with_column_names() -> None:
    line, filled = _serialize("|STT|Môn|Điểm|", "|1|Toán|9|")

    assert line == "STT: 1; Môn: Toán; Điểm: 9"
    assert filled == ["1", "Toán", "9"]


def test_merged_leading_cells_are_filled_from_row_above() -> None:
    header = "|GA|Mô tả|ULO|ULO con|"
    first, filled = _serialize(header, "|GA1|Tri thức|ULO1: Khả năng|ULO1.2: Phân tích|")
    second, filled = _serialize(header, "||||ULO1.3: Ứng dụng phương pháp|", filled)
    third, _ = _serialize(header, "||||ULO1.4: Tự học|", filled)

    assert first == "GA: GA1; Mô tả: Tri thức; ULO: ULO1: Khả năng; ULO con: ULO1.2: Phân tích"
    assert second == "GA: GA1; Mô tả: Tri thức; ULO: ULO1: Khả năng; ULO con: ULO1.3: Ứng dụng phương pháp"
    assert third.startswith("GA: GA1; Mô tả: Tri thức; ULO: ULO1: Khả năng; ")
    assert third.endswith("ULO con: ULO1.4: Tự học")


def test_empty_cells_after_first_value_are_not_filled() -> None:
    # Bảng khung kỷ luật: ô trống nghĩa là "không áp dụng", không phải gộp ô.
    header = "|TT|Nội dung vi phạm|Khiển trách|Cảnh cáo|Ghi chú|"
    _, filled = _serialize(header, "|5.|Đánh bạc|1|2|Báo công an|")
    line, filled = _serialize(header, "|6.|Thi hộ|||Xử lý theo quy chế|", filled)

    assert line == "TT: 6.; Nội dung vi phạm: Thi hộ; Ghi chú: Xử lý theo quy chế"
    assert "Khiển trách" not in line
    assert filled == ["6.", "Thi hộ", "", "", "Xử lý theo quy chế"]


def test_cell_still_empty_after_fill_is_dropped() -> None:
    line, _ = _serialize("|A|B|C|", "|||giá trị C|", ["", "b trên"])

    assert line == "B: b trên; C: giá trị C"


def test_br_in_header_and_cells_becomes_space() -> None:
    line, filled = _serialize(
        "|Họ và<br/>tên|Điện<br>thoại|", "|GS.TS. Phạm Ngọc<br/>Anh|0912 316<br/>141|"
    )

    assert line == "Họ và tên: GS.TS. Phạm Ngọc Anh; Điện thoại: 0912 316 141"
    assert filled == ["GS.TS. Phạm Ngọc Anh", "0912 316 141"]


def test_unnamed_header_column_keeps_bare_value() -> None:
    line, _ = _serialize("|Phẩm chất||Chuẩn đầu ra||", "|GA2|Đạo đức|ULO2|ULO2.1|")

    assert line == "Phẩm chất: GA2; Đạo đức; Chuẩn đầu ra: ULO2; ULO2.1"


def test_all_empty_row_keeps_previous_fill() -> None:
    line, filled = _serialize("|A|B|", "| | |", ["a", "b"])

    assert line == ""
    assert filled == ["a", "b"]


def test_row_wider_or_narrower_than_header() -> None:
    wide, _ = _serialize("|A|B|", "|1|2|3|")
    narrow, filled = _serialize("|A|B|C|", "|1|2|")

    assert wide == "A: 1; B: 2; 3"
    assert narrow == "A: 1; B: 2"
    assert filled == ["1", "2", ""]


_SPLIT_TABLE = (
    "## Chuẩn đầu ra\n\n"
    "|Phẩm chất|Mô tả|Chuẩn đầu ra|\n|-|-|-|\n"
    + "\n".join(
        f"|GA1|Tri thức – Sáng tạo|ULO1.{index}: {'nội dung chuẩn đầu ra rất dài ' * 3}|"
        if index == 1
        else f"|||ULO1.{index}: {'nội dung chuẩn đầu ra rất dài ' * 3}|"
        for index in range(1, 13)
    )
    + "\n"
)


def _children(text: str) -> list[str]:
    return [
        chunk.text
        for chunk in split_parent_child(
            text, parent_size=800, parent_overlap=0, child_size=400, child_overlap=0, min_child_size=0
        )
    ]


def test_fill_crosses_child_boundary_with_document_index() -> None:
    children = _children(_SPLIT_TABLE)
    assert len(children) > 1, "fixture phải bị tách thành nhiều child"
    # Child sau không chứa hàng GA1 — giá trị gộp ô nằm ở child trước.
    later = next(child for child in children[1:] if "|GA1|" not in child and "|||ULO1." in child)
    first_row = next(line for line in later.splitlines() if line.startswith("|||ULO1."))

    row_index = table_row_search_index(clean_text(_SPLIT_TABLE))
    body = table_search_body(later, row_index)
    ulo = first_row.split("|")[3].split(":")[0]

    assert f"Phẩm chất: GA1; Mô tả: Tri thức – Sáng tạo; Chuẩn đầu ra: {ulo}:" in body
    # Không có chỉ mục tài liệu thì child chỉ biết những gì nằm trong nó.
    assert "GA1" not in table_search_body(later)


def test_table_search_body_replaces_markdown_table_and_keeps_prose() -> None:
    text = "### Liên hệ\n\nLãnh đạo khoa:\n\n|Đơn vị|Họ tên|\n|-|-|\n|Khoa|TS. A|\n|BM Toán|TS. B|"

    body = table_search_body(text)

    assert body == "### Liên hệ\n\nLãnh đạo khoa:\n\nĐơn vị: Khoa; Họ tên: TS. A\nĐơn vị: BM Toán; Họ tên: TS. B"
    assert "|" not in body


def test_table_search_body_without_table_is_unchanged() -> None:
    text = "Sinh viên nộp hồ sơ tại phòng một cửa.\n\nKhông có bảng | nào ở đây."

    assert table_search_body(text) == text


def test_header_only_table_keeps_header_content() -> None:
    # LlamaParse hay coi hàng dữ liệu duy nhất là header.
    body = table_search_body("|1|TS Đoàn<br/>Hiếu|Trưởng khoa|0934 683 131|\n|-|-|-|-|")

    assert body == "1; TS Đoàn Hiếu; Trưởng khoa; 0934 683 131"


def test_html_table_is_kept_verbatim() -> None:
    html = "<table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>"
    text = f"Mở đầu.\n\n{html}\n\n|A|B|\n|-|-|\n|1|2|"

    body = table_search_body(text)

    assert html in body
    assert "A: 1; B: 2" in body


def test_data_file_d26_rows_are_serialized_with_context() -> None:
    candidates = list(Path(settings.documents_path).rglob("*.md"))
    if not candidates:
        pytest.skip("Thiếu file dữ liệu D26 trong data/ (thư mục bị gitignore).")
    text = max(candidates, key=lambda path: path.stat().st_size).read_text(encoding="utf-8")
    row_index = table_row_search_index(clean_text(text))
    children = [
        chunk.text
        for chunk in split_parent_child(
            text,
            parent_size=settings.chunk_size,
            parent_overlap=settings.chunk_overlap,
            child_size=settings.child_chunk_size,
            child_overlap=settings.child_chunk_overlap,
            min_child_size=settings.min_child_chunk_chars,
        )
    ]
    bodies = {child: table_search_body(child, row_index) for child in children}

    table_children = [child for child in children if "\n|-|" in child]
    assert len(table_children) > 300
    for child in table_children:
        assert not any(line.startswith("|") for line in bodies[child].splitlines()), child[:120]

    ulo = next(child for child in children if "||||ULO1.3" in child)
    ulo_line = next(line for line in bodies[ulo].splitlines() if "ULO1.3" in line)
    assert ulo_line.startswith("Phẩm chất người tốt nghiệp (Graduate Attributes): GA1;")

    contact = next(child for child in children if "|Lãnh đạo<br/>Khoa|GS.TS. Phạm Ngọc<br/>Anh|" in child)
    assert "ĐƠN VỊ: Lãnh đạo Khoa; HỌ VÀ TÊN: GS.TS. Phạm Ngọc Anh; CHỨC VỤ: Trưởng khoa; ĐIỆN THOẠI: 0912 316 141" in bodies[contact]

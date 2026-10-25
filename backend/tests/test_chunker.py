from app.ingestion.chunker import (
    _table_cells_safe,
    compose_search_text,
    split_parent_child,
    split_text,
)
from app.ingestion.cleaner import clean_text


def _clause(number: int, article: int) -> str:
    return (
        f"{number}. Khoản thứ {number} của Điều {article} quy định về nghĩa vụ học tập "
        "của sinh viên trong học kỳ chính và học kỳ phụ."
    )


def test_split_text_keeps_markdown_section_metadata() -> None:
    text = """# Handbook

Intro text.

## Tuition

Tuition policy paragraph.

### Late Payment

Late payment details.
"""

    chunks = split_text(text, chunk_size=120, chunk_overlap=20)

    assert [chunk.heading for chunk in chunks] == ["Handbook", "Tuition", "Late Payment"]
    assert chunks[2].section_path == "Handbook > Tuition > Late Payment"
    assert chunks[2].heading_level == 3


def test_split_text_splits_long_section_without_losing_heading_context() -> None:
    text = """## Academic Warning

""" + "\n\n".join(f"Paragraph {index} has enough content to force section splitting." for index in range(8))

    chunks = split_text(text, chunk_size=160, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(chunk.heading == "Academic Warning" for chunk in chunks)
    assert all(chunk.section_path == "Academic Warning" for chunk in chunks)
    assert all(chunk.text.startswith("## Academic Warning") for chunk in chunks)
    assert all(len(chunk.text) <= 160 for chunk in chunks)
    assert all(chunk.text.strip() != "## Academic Warning" for chunk in chunks)


def test_split_text_does_not_create_heading_only_chunks() -> None:
    text = """## A

""" + ("A long paragraph with useful information. " * 20)

    chunks = split_text(text, chunk_size=120, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(chunk.text.startswith("## A\n\n") for chunk in chunks)
    assert all(chunk.text.strip() != "## A" for chunk in chunks)
    assert all(len(chunk.text) <= 120 for chunk in chunks)


def test_split_text_skips_section_with_only_a_heading() -> None:
    text = """# Parent

## Child

Child content.
"""

    chunks = split_text(text, chunk_size=120, chunk_overlap=20)

    assert [chunk.heading for chunk in chunks] == ["Child"]
    assert chunks[0].section_path == "Parent > Child"


def test_split_text_splits_markdown_table_between_rows_and_repeats_header() -> None:
    rows = "\n".join(
        f"| Program-{index} | {100000 + index} |" for index in range(1, 13)
    )
    text = f"""## Tuition fees

Introductory paragraph immediately before the table.
| Program | Fee |
|---|---:|
{rows}

Closing paragraph.
"""

    chunks = split_text(text, chunk_size=125, chunk_overlap=20)
    table_chunks = [chunk for chunk in chunks if "| Program | Fee |" in chunk.text]

    assert len(table_chunks) > 1
    assert all("|---|---:|" in chunk.text for chunk in table_chunks)
    assert sum(chunk.text.count("| Program-1 |") for chunk in table_chunks) == 1
    assert sum(chunk.text.count("| Program-12 |") for chunk in table_chunks) == 1
    assert all(chunk.heading == "Tuition fees" for chunk in table_chunks)
    assert max(
        sum(1 for line in chunk.text.splitlines() if line.startswith("| Program-"))
        for chunk in table_chunks
    ) >= 3


def test_split_text_does_not_cut_an_oversized_table_row() -> None:
    long_cell = "important policy detail " * 12
    text = f"""## Policy

| Rule | Description |
|---|---|
| A | {long_cell}|
"""

    chunks = split_text(text, chunk_size=100, chunk_overlap=20)

    assert len(chunks) == 1
    assert long_cell.strip() in chunks[0].text
    assert "| Rule | Description |" in chunks[0].text


def test_parent_child_chunking_keeps_large_parent_for_each_small_child() -> None:
    text = """## Điều 10. Học phí

""" + "\n\n".join(
        f"{index}. Nội dung quy định học phí dành cho sinh viên trong trường hợp {index}."
        for index in range(1, 9)
    )

    chunks = split_parent_child(
        text,
        parent_size=360,
        parent_overlap=40,
        child_size=150,
        child_overlap=30,
    )

    assert len(chunks) > 2
    assert all(chunk.parent_text for chunk in chunks)
    assert all(len(chunk.text) <= 150 for chunk in chunks)
    assert all(len(chunk.parent_text) >= len(chunk.text) for chunk in chunks)
    assert all(chunk.heading == "Điều 10. Học phí" for chunk in chunks)
    assert {chunk.parent_index for chunk in chunks} == {0, 1}
    assert chunks[0].child_index == 0


def test_parent_child_inherits_full_section_path_from_parent() -> None:
    text = """# Handbook

## Tuition

### Late fees

""" + "\n\n".join(
        f"Detail paragraph {index} about late payment policy for students and parents."
        for index in range(1, 10)
    )

    chunks = split_parent_child(
        text,
        parent_size=400,
        parent_overlap=40,
        child_size=160,
        child_overlap=30,
    )

    assert chunks
    assert all(chunk.heading == "Late fees" for chunk in chunks)
    assert all(chunk.section_path == "Handbook > Tuition > Late fees" for chunk in chunks)
    assert all(chunk.heading_level == 3 for chunk in chunks)


def test_clean_text_replaces_form_feed_and_vertical_tab() -> None:
    cleaned = clean_text("alpha\fbeta\vgamma\n\n\ndelta")

    assert "\f" not in cleaned
    assert "\v" not in cleaned
    assert "alpha beta gamma" in cleaned
    assert "\n\n\n" not in cleaned


def test_split_text_keeps_table_intact_when_form_feed_breaks_latex() -> None:
    text = r"""## Metrics

| Name | Formula | Note |
| :--- | :--- | :--- |
| Cosine | $S = \frac{A}{B}$ | ok |
| Other | $x$ | fine |
"""
    # Simulate corrupted LaTeX where \f became a real form-feed character.
    text = text.replace(r"\frac", "\frac")

    chunks = split_text(text, chunk_size=500, chunk_overlap=20)
    table_chunks = [chunk for chunk in chunks if "| Name | Formula | Note |" in chunk.text]

    assert len(table_chunks) == 1
    assert "Cosine" in table_chunks[0].text
    assert "Other" in table_chunks[0].text
    assert "| :--- | :--- | :--- |" in table_chunks[0].text


def test_parent_child_repeats_table_header_on_oversized_children() -> None:
    rows = "\n".join(f"| Item-{index:02d} | Value {index} description |" for index in range(1, 16))
    text = f"""# Catalog

## Products

| Name | Description |
| :--- | :--- |
{rows}
"""

    chunks = split_parent_child(
        text,
        parent_size=900,
        parent_overlap=50,
        child_size=280,
        child_overlap=40,
    )
    table_children = [chunk for chunk in chunks if "| Item-" in chunk.text]

    assert len(table_children) > 1
    assert all("| Name | Description |" in chunk.text for chunk in table_children)
    assert all("| :--- | :--- |" in chunk.text for chunk in table_children)
    assert all(chunk.section_path == "Catalog > Products" for chunk in table_children)
    # Soft packing should keep multiple data rows per child when possible.
    data_row_counts = [
        sum(1 for line in chunk.text.splitlines() if line.startswith("| Item-"))
        for chunk in table_children
    ]
    assert max(data_row_counts) >= 3


def test_wide_table_does_not_collapse_to_one_row_per_chunk() -> None:
    rows = "\n".join(
        "| TX-{index:03d} | 2026-01-{index:02d} | 1029384756 | 15.000.000 | "
        "Chuyển khoản | Thành công | Thanh toán hóa đơn {index} |".format(index=index)
        for index in range(1, 13)
    )
    text = f"""## Giao dịch

| Mã Giao Dịch | Ngày Thực Hiện | Tài Khoản Nguồn | Số Tiền (VND) | Loại Giao Dịch | Trạng Thái | Ghi Chú |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{rows}
"""

    children = split_parent_child(
        text,
        parent_size=900,
        parent_overlap=100,
        child_size=300,
        child_overlap=50,
    )
    tx_children = [chunk for chunk in children if "| TX-" in chunk.text]
    assert tx_children
    assert all("Mã Giao Dịch" in chunk.text for chunk in tx_children)

    rows_per_child = [
        sum(1 for line in chunk.text.splitlines() if "| TX-" in line)
        for chunk in tx_children
    ]
    assert max(rows_per_child) >= 3
    assert sum(1 for count in rows_per_child if count == 1) <= 1
    assert sum(rows_per_child) == 12


def test_table_cells_safe_ignores_escaped_and_fenced_pipes() -> None:
    line = r"| Dot | `a \| b` | $x \| y$ | ok \|"
    # Row intentionally missing trailing pipe after escaped pipe content style
    line = "| Dot | `a \\| b` | $x \\| y$ | note |"
    cells = _table_cells_safe(line)

    assert len(cells) == 4
    assert "`a \\| b`" in cells[1]
    assert "$x \\| y$" in cells[2]


def test_split_text_keeps_multiline_markdown_table_cells() -> None:
    text = """## Config

| Category | Parameter | Action |
| :--- | :--- | :--- |
| Strategy | chunk_size | Keep size small. |
| | keep_separator | Keep separators like `

` and `|` intact. |
| Table | repeat_header | Enabled. |
"""

    chunks = split_text(text, chunk_size=800, chunk_overlap=40)

    assert len(chunks) == 1
    assert "keep_separator" in chunks[0].text
    assert "repeat_header" in chunks[0].text
    assert "| Category | Parameter | Action |" in chunks[0].text
    # Incomplete open-row + blank line must not create an orphan fragment chunk.
    assert not any(
        line.strip().startswith("`") and "repeat_header" not in chunk.text
        for chunk in chunks
        for line in chunk.text.splitlines()[:3]
    )


def test_split_text_merges_short_intro_with_first_table_chunk() -> None:
    rows = "\n".join(
        f"| TX-{index:03d} | 1000 | note for transaction {index} |" for index in range(1, 12)
    )
    text = f"""## Transactions

Short intro before the wide table.
| Code | Amount | Note |
| :--- | :--- | :--- |
{rows}
"""

    chunks = split_text(text, chunk_size=220, chunk_overlap=20)
    first_table = next(chunk for chunk in chunks if "| Code | Amount | Note |" in chunk.text)

    assert "Short intro before the wide table." in first_table.text
    assert "| TX-001 |" in first_table.text


def test_split_text_drops_horizontal_rule_only_blocks() -> None:
    text = """## Section

Paragraph before rule.

---

Paragraph after rule.
"""

    chunks = split_text(text, chunk_size=500, chunk_overlap=20)

    assert len(chunks) == 1
    assert "---" not in chunks[0].text.splitlines()
    assert "Paragraph before rule." in chunks[0].text
    assert "Paragraph after rule." in chunks[0].text


def test_split_text_keeps_html_table_atomic_and_splits_by_row() -> None:
    body_rows = "\n".join(
        f"    <tr><td>Region-{index}</td><td>{index * 1000}</td><td>+{index}%</td></tr>"
        for index in range(1, 10)
    )
    text = f"""## Regions

<table>
  <thead>
    <tr><th>Region</th><th>Revenue</th><th>Growth</th></tr>
  </thead>
  <tbody>
{body_rows}
  </tbody>
</table>
"""

    chunks = split_text(text, chunk_size=280, chunk_overlap=20)
    html_chunks = [chunk for chunk in chunks if "<table" in chunk.text.lower()]

    assert html_chunks
    assert all("<thead>" in chunk.text.lower() for chunk in html_chunks)
    assert all("</table>" in chunk.text.lower() for chunk in html_chunks)
    assert sum(chunk.text.count("Region-") for chunk in html_chunks) == 9


# ---------------------------------------------------------------------------
# RAG-06: parent theo Điều/Khoản, cắt theo ranh giới câu, gộp chunk ngắn
# ---------------------------------------------------------------------------


def test_split_parent_child_parent_is_one_article() -> None:
    text = "\n\n".join(
        [
            "### Điều 1. Học phí",
            *(_clause(number, 1) for number in range(1, 5)),
            "### Điều 2. Bảo hiểm y tế",
            *(_clause(number, 2) for number in range(1, 5)),
        ]
    )

    chunks = split_parent_child(
        text,
        parent_size=200,
        parent_overlap=0,
        child_size=180,
        child_overlap=0,
        min_child_size=100,
    )

    parents = {}
    for chunk in chunks:
        parents.setdefault(chunk.parent_index, chunk.parent_text)
    assert len(parents) > 2
    for parent_text in parents.values():
        article_headings = [
            line
            for line in parent_text.splitlines()
            if line.startswith("#") and "Điều" in line
        ]
        assert len(article_headings) == 1
        numbers = {line for line in parent_text.splitlines() if "Khoản thứ" in line}
        article_number = article_headings[0].split()[2].rstrip(".")
        # Nội dung Khoản luôn ghi số Điều của chính parent đó.
        assert all(f"Điều {article_number} " in line for line in numbers)


def test_split_parent_child_groups_consecutive_clauses_within_article() -> None:
    # Một Điều dài vượt parent_size: parent thứ hai nhóm tiếp các Khoản kế tiếp,
    # nhưng không bao giờ trộn sang Điều khác.
    text = "\n\n".join(
        ["### Điều 9. Nội trú", *(_clause(number, 9) for number in range(1, 7))]
    )

    chunks = split_parent_child(
        text,
        parent_size=260,
        parent_overlap=0,
        child_size=240,
        child_overlap=0,
        min_child_size=100,
    )

    parents = {}
    for chunk in chunks:
        parents.setdefault(chunk.parent_index, chunk.parent_text)
    assert len(parents) >= 2
    for parent_text in parents.values():
        assert parent_text.count("Điều 9") >= 1
        assert "Điều 1." not in parent_text and "Điều 2." not in parent_text


def test_split_parent_child_guide_document_parent_is_section() -> None:
    text = "\n\n".join(
        [
            "## Hướng dẫn làm vé tháng xe bus",
            "Bước 1. Sinh viên chuẩn bị thẻ sinh viên và giấy tờ tùy thân.",
            "Bước 2. Đăng ký online qua cổng dịch vụ của Học viện.",
            "Bước 3. Nhận vé tại văn phòng một cửa sau ba ngày làm việc.",
            "## Hướng dẫn cấp giấy xác nhận sinh viên",
            "Sinh viên nộp đơn tại phòng Đào tạo và nhận sau hai ngày.",
        ]
    )

    chunks = split_parent_child(
        text,
        parent_size=300,
        parent_overlap=0,
        child_size=200,
        child_overlap=0,
        min_child_size=80,
    )

    parents = {chunk.parent_index: chunk for chunk in chunks}
    assert len(parents) == 2
    by_heading = {chunk.heading for chunk in chunks}
    assert by_heading == {
        "Hướng dẫn làm vé tháng xe bus",
        "Hướng dẫn cấp giấy xác nhận sinh viên",
    }


def test_split_long_block_respects_sentence_boundaries() -> None:
    text = "\n\n".join(
        [
            "### Điều 5. Thời hạn đăng ký",
            " ".join(
                f"Câu thứ {index} mô tả quy định đăng ký học phần cho sinh viên năm thứ nhất."
                for index in range(1, 15)
            ),
        ]
    )

    chunks = split_parent_child(
        text,
        parent_size=5000,
        parent_overlap=0,
        child_size=150,
        child_overlap=0,
        min_child_size=100,
    )

    assert len(chunks) > 1
    for chunk in chunks:
        body = chunk.text.split("\n", 1)[1].strip()
        assert body[0].isupper() or body[0].isdigit()
        assert len(chunk.text) <= 150


def test_oversized_sentence_splits_at_word_boundary() -> None:
    long_sentence = (
        "Sinh viên " + "được miễn giảm học phí trong trường hợp đặc biệt " * 12
    ).strip() + "."

    chunks = split_parent_child(
        f"### Điều 7. Miễn giảm\n\n{long_sentence}",
        parent_size=5000,
        parent_overlap=0,
        child_size=120,
        child_overlap=0,
        min_child_size=100,
    )

    assert len(chunks) > 1
    # Mỗi piece phải là đoạn con của câu gốc, cắt chỉ xảy ra tại khoảng trắng.
    cursor = 0
    for chunk in chunks:
        body = chunk.text.split("\n", 1)[1].strip()
        start = long_sentence.find(body, cursor)
        assert start >= cursor, body[:30]
        assert long_sentence[cursor:start].strip() == ""
        cursor = start + len(body)


def test_short_tail_merges_into_previous_child() -> None:
    text = "\n\n".join(
        ["### Điều 3. Cảnh báo học tập"]
        + [
            f"Khoản {index}. Sinh viên bị cảnh báo học tập khi tổng điểm trung bình "
            "tích lũy của học phần đã đăng ký không đạt ngưỡng tối thiểu."
            for index in range(1, 6)
        ]
    )

    chunks = split_parent_child(
        text,
        parent_size=5000,
        parent_overlap=0,
        child_size=260,
        child_overlap=0,
        min_child_size=120,
    )

    body_lengths = [
        len(chunk.text.split("\n", 1)[1].strip())
        for chunk in chunks
        if "\n" in chunk.text
    ]
    assert len(chunks) >= 2
    assert all(length >= 100 for length in body_lengths)


def test_short_section_keeps_single_short_chunk() -> None:
    text = "### Điều 4. Điều khoản tham chiếu\n\nTheo quy định của Học viện."

    chunks = split_parent_child(
        text,
        parent_size=900,
        parent_overlap=0,
        child_size=450,
        child_overlap=0,
        min_child_size=120,
    )

    assert len(chunks) == 1
    assert len(chunks[0].text) < 120


def test_trailing_note_after_table_attaches_to_table_chunk() -> None:
    rows = "\n".join(
        f"| HP-{index:02d} | Môn học tự chọn số {index} | {index} tín chỉ |"
        for index in range(1, 12)
    )
    text = f"""### Học phần tự chọn

| Mã HP | Tên học phần | Số tín chỉ |
|---|---|---|
{rows}

Chi tiết về chương trình đào tạo sinh viên xem tại: https://daotao.ptit.edu.vn/ctdt/
"""

    chunks = split_parent_child(
        text,
        parent_size=5000,
        parent_overlap=0,
        child_size=300,
        child_overlap=0,
        min_child_size=120,
    )

    note_chunks = [chunk for chunk in chunks if "xem tại" in chunk.text]
    assert len(note_chunks) == 1
    assert "| Mã HP |" in note_chunks[0].text


def test_compose_search_text_prefixes_document_and_section_path() -> None:
    composed = compose_search_text(
        "Sổ tay sinh viên D26",
        "QUY ĐỊNH ĐÀO TẠO > Chương VI > Điều 33. Cảnh báo kết quả học tập",
        "Sinh viên bị cảnh báo khi điểm trung bình tích lũy dưới mức quy định.",
    )

    assert composed.startswith(
        "Sổ tay sinh viên D26 > QUY ĐỊNH ĐÀO TẠO > Chương VI > Điều 33. Cảnh báo kết quả học tập\n"
    )
    assert composed.endswith(
        "Sinh viên bị cảnh báo khi điểm trung bình tích lũy dưới mức quy định."
    )


def test_compose_search_text_without_section_path() -> None:
    assert compose_search_text("TB nội trú", "", "Nội dung thông báo.") == "TB nội trú\nNội dung thông báo."
    assert compose_search_text("", "", "Nội dung thông báo.") == "Nội dung thông báo."


# ---------------------------------------------------------------------------
# RAG-06: cleaner lọc nhiễu
# ---------------------------------------------------------------------------


def test_clean_text_drops_toc_dot_leader_entries() -> None:
    text = "# MỤC LỤC\n\nLời nói đầu ............ 3\nHọc phí .............. 12\n\nNội dung thật."

    cleaned = clean_text(text)

    assert "Lời nói đầu" not in cleaned
    assert "Học phí ......" not in cleaned
    assert "Nội dung thật." in cleaned


def test_clean_text_drops_whole_toc_section_including_tables() -> None:
    text = "\n".join(
        [
            "# MỤC LỤC",
            "",
            "Điều 1. Học phí 5",
            "Điều 2. Bảo hiểm 7",
            "| Nội dung | Trang |",
            "|---|---|",
            "| Học phí | 12 |",
            "",
            "# PHẦN I: TỔNG QUAN",
            "",
            "Nội dung thật.",
        ]
    )

    cleaned = clean_text(text)

    assert "MỤC LỤC" not in cleaned
    assert "Điều 1. Học phí" not in cleaned
    assert "| Học phí | 12 |" not in cleaned
    assert "# PHẦN I: TỔNG QUAN" in cleaned
    assert "Nội dung thật." in cleaned


def test_clean_text_drops_toc_entries_with_two_dots() -> None:
    text = "Quy định tổ chức thi kết thúc học phần.. 145\n\nNội dung thật."

    cleaned = clean_text(text)

    assert "145" not in cleaned
    assert "Nội dung thật." in cleaned


def test_clean_text_keeps_form_lines_with_multiple_blank_runs() -> None:
    line = "Họ và tên: .................. Nam (Nữ): ....................."

    cleaned = clean_text(line)

    assert line in cleaned




def test_clean_text_drops_bold_heading_with_page_number() -> None:
    text = "## **PHẦN III: CHƯƠNG TRÌNH VÀ KẾ HOẠCH ĐÀO TẠO** **24**\n\nNội dung."

    cleaned = clean_text(text)

    assert "PHẦN III" not in cleaned
    assert "Nội dung." in cleaned


def test_clean_text_drops_page_numbers() -> None:
    cleaned = clean_text("Văn bản.\n\n- 3 -\n\n7\n\nTiếp theo.")

    assert "- 3 -" not in cleaned
    assert "\n7\n" not in cleaned
    assert "Tiếp theo." in cleaned


def test_clean_text_drops_national_title_motto_and_dateline() -> None:
    text = "\n".join(
        [
            "# CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM Độc lập - Tự do - Hạnh phúc",
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
            "Độc lập - Tự do - Hạnh phúc",
            "Hà Nội, ngày 05 tháng 9 năm 2026",
            "Hà Nội, ngày tháng 8 năm 2026",
            "Nội dung thông báo.",
        ]
    )

    cleaned = clean_text(text)

    assert "CỘNG HOÀ" not in cleaned
    assert "Độc lập" not in cleaned
    assert "Hà Nội, ngày" not in cleaned
    assert "Nội dung thông báo." in cleaned


def test_clean_text_drops_signature_block_and_distribution_list() -> None:
    text = "\n".join(
        [
            "Nội dung thông báo.",
            "# Nơi nhận",
            "- Ban GĐHV (b/c);",
            "- Phòng GV (t/h);",
            "- Lưu VT, CT&CTSV.",
            "",
            "# TRƯỞNG PHÒNG",
            "(đã ký)",
            "Nguyễn Chí Thành",
            "Nội dung sau chữ ký cần giữ nếu có.",
        ]
    )

    cleaned = clean_text(text)

    assert "Nơi nhận" not in cleaned
    assert "(b/c)" not in cleaned
    assert "TRƯỞNG PHÒNG" not in cleaned
    assert "đã ký" not in cleaned
    assert "Nguyễn Chí Thành" not in cleaned
    assert "Nội dung thông báo." in cleaned
    assert "Nội dung sau chữ ký cần giữ nếu có." in cleaned


def test_clean_text_keeps_signer_context_lines_in_prose() -> None:
    text = "\n".join(
        [
            "Trưởng phòng Đào tạo thông báo lịch thi cho toàn bộ sinh viên.",
            "Thư ký hội đồng thông qua danh sách người học được lựa chọn.",
        ]
    )

    cleaned = clean_text(text)

    assert "Trưởng phòng Đào tạo" in cleaned
    assert "Thư ký hội đồng" in cleaned


def test_clean_text_drops_scan_watermark() -> None:
    cleaned = clean_text("lOMoARcPSD|40036395\n\nNội dung tài liệu.")

    assert "lOMoARcPSD" not in cleaned
    assert "Nội dung tài liệu." in cleaned


def test_clean_text_never_touches_tables_and_fences() -> None:
    text = "\n".join(
        [
            "| Mục lục | Trang |",
            "|---|---|",
            "| Học phí | 12 |",
            "",
            "```",
            "# CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM",
            "```",
        ]
    )

    cleaned = clean_text(text)

    assert "| Mục lục | Trang |" in cleaned
    assert "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM" in cleaned

from app.ingestion.chunker import (
    _table_cells_safe,
    split_parent_child,
    split_text,
)
from app.ingestion.cleaner import clean_text


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

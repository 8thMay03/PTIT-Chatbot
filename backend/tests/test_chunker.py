from app.ingestion.chunker import split_text


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
    text = """## Tuition fees

Introductory paragraph immediately before the table.
| Program | Fee |
|---|---:|
| Information Technology | 123456 |
| Electronics Engineering | 234567 |
| Business Administration | 345678 |
| Multimedia | 456789 |

Closing paragraph.
"""

    chunks = split_text(text, chunk_size=125, chunk_overlap=20)
    table_chunks = [chunk for chunk in chunks if "| Program | Fee |" in chunk.text]

    assert len(table_chunks) > 1
    assert all("|---|---:|" in chunk.text for chunk in table_chunks)
    assert sum(chunk.text.count("| Information Technology | 123456 |") for chunk in table_chunks) == 1
    assert sum(chunk.text.count("| Electronics Engineering | 234567 |") for chunk in table_chunks) == 1
    assert sum(chunk.text.count("| Business Administration | 345678 |") for chunk in table_chunks) == 1
    assert sum(chunk.text.count("| Multimedia | 456789 |") for chunk in table_chunks) == 1
    assert all(chunk.heading == "Tuition fees" for chunk in table_chunks)


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

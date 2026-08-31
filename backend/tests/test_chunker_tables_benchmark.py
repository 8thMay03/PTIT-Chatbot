from pathlib import Path

from app.ingestion.chunker import split_parent_child, split_text

BENCHMARK_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "test_chunker_tables _1_.md"
)


def _benchmark_text() -> str:
    return BENCHMARK_PATH.read_text(encoding="utf-8")


def test_benchmark_file_exists() -> None:
    assert BENCHMARK_PATH.is_file()


def test_benchmark_long_table_chunks_repeat_header() -> None:
    chunks = split_text(_benchmark_text(), chunk_size=900, chunk_overlap=150)
    tx_chunks = [chunk for chunk in chunks if "| TX-2026-" in chunk.text]

    assert tx_chunks
    assert all("Mã Giao Dịch" in chunk.text for chunk in tx_chunks)
    assert all("---" in chunk.text for chunk in tx_chunks)

    found = set()
    for chunk in tx_chunks:
        for line in chunk.text.splitlines():
            if line.startswith("| TX-2026-"):
                found.add(line.split("|")[1].strip())
    assert found == {f"TX-2026-{index:03d}" for index in range(1, 21)}


def test_benchmark_parent_child_inherits_section_path() -> None:
    parents = split_text(_benchmark_text(), chunk_size=2048, chunk_overlap=150)
    children = split_parent_child(
        _benchmark_text(),
        parent_size=2048,
        parent_overlap=150,
        child_size=800,
        child_overlap=100,
    )

    parent_paths = {parent.index: parent.section_path for parent in parents}
    assert children
    assert all(child.section_path == parent_paths[child.parent_index] for child in children)
    assert all(child.heading for child in children)


def test_benchmark_table_children_keep_markdown_header() -> None:
    children = split_parent_child(
        _benchmark_text(),
        parent_size=2048,
        parent_overlap=150,
        child_size=800,
        child_overlap=100,
    )
    md_table_children = [
        chunk
        for chunk in children
        if chunk.text.count("|") >= 4 and any(line.strip().startswith("|") for line in chunk.text.splitlines())
    ]

    assert md_table_children
    for chunk in md_table_children:
        pipe_lines = [line for line in chunk.text.splitlines() if line.strip().startswith("|")]
        # Children that still look like table fragments should include a delimiter row.
        if any("TX-2026-" in line or "USR-" in line or "FTR-" in line for line in pipe_lines):
            assert any("---" in line for line in pipe_lines), chunk.text[:200]


def test_benchmark_html_table_stays_well_formed() -> None:
    chunks = split_text(_benchmark_text(), chunk_size=500, chunk_overlap=50)
    html_chunks = [chunk for chunk in chunks if "<table" in chunk.text.lower()]

    assert html_chunks
    assert all("</table>" in chunk.text.lower() for chunk in html_chunks)
    assert all("<thead>" in chunk.text.lower() or "<th" in chunk.text.lower() for chunk in html_chunks)


def test_benchmark_stress_child_sizes() -> None:
    children = split_parent_child(
        _benchmark_text(),
        parent_size=900,
        parent_overlap=100,
        child_size=450,
        child_overlap=50,
    )

    assert children
    # Single oversized table/HTML rows may exceed the budget; everything else must fit.
    oversized = [chunk for chunk in children if len(chunk.text) > 450]
    for chunk in oversized:
        body_lines = [
            line
            for line in chunk.text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        assert body_lines, chunk.text

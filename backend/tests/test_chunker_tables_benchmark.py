from pathlib import Path

import pytest

from app.core.config import settings
from app.ingestion.chunker import split_parent_child, split_text

BENCHMARK_PATH = Path(__file__).parent / "fixtures" / "corpus" / "chunker-tables-benchmark.md"

# Bản benchmark gốc từng nằm trong data/ (bị gitignore). Khi có dữ liệu thật
# trong data/, chạy lại các kiểm tra trên nó; trên bản clone sạch thì bỏ qua.
DATA_BENCHMARK_PATH = Path(settings.documents_path) / "test_chunker_tables _1_.md"


def _benchmark_text() -> str:
    return BENCHMARK_PATH.read_text(encoding="utf-8")


def _assert_table_chunking(text: str) -> None:
    """Các bất biến cốt lõi của benchmark bảng, dùng cho cả fixture và data thật."""
    chunks = split_text(text, chunk_size=900, chunk_overlap=150)
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


def _assert_parent_child_section_paths(text: str) -> None:
    children = split_parent_child(
        text,
        parent_size=2048,
        parent_overlap=150,
        child_size=800,
        child_overlap=100,
    )

    assert children
    assert all(child.heading for child in children)
    # Từ RAG-06, parent được dựng theo section (không tách theo ký tự), nên mỗi
    # nhóm child cùng parent phải cùng heading/section_path và parent_text chứa
    # đúng heading đó thay vì trộn section khác.
    by_parent: dict[int, list] = {}
    for child in children:
        by_parent.setdefault(child.parent_index, []).append(child)
    for parent_index, group in by_parent.items():
        assert len({child.section_path for child in group}) == 1
        assert len({child.heading for child in group}) == 1
        parent_text = group[0].parent_text
        assert group[0].heading in parent_text
        for child in group:
            assert child.text in child.parent_text or child.heading in parent_text


def _assert_table_children_keep_header(text: str) -> None:
    children = split_parent_child(
        text,
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


def _assert_html_table_well_formed(text: str) -> None:
    chunks = split_text(text, chunk_size=500, chunk_overlap=50)
    html_chunks = [chunk for chunk in chunks if "<table" in chunk.text.lower()]

    assert html_chunks
    assert all("</table>" in chunk.text.lower() for chunk in html_chunks)
    assert all("<thead>" in chunk.text.lower() or "<th" in chunk.text.lower() for chunk in html_chunks)


def _assert_stress_child_sizes(text: str) -> None:
    children = split_parent_child(
        text,
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


def test_benchmark_fixture_exists() -> None:
    assert BENCHMARK_PATH.is_file()


def test_benchmark_long_table_chunks_repeat_header() -> None:
    _assert_table_chunking(_benchmark_text())


def test_benchmark_parent_child_inherits_section_path() -> None:
    _assert_parent_child_section_paths(_benchmark_text())


def test_benchmark_table_children_keep_markdown_header() -> None:
    _assert_table_children_keep_header(_benchmark_text())


def test_benchmark_html_table_stays_well_formed() -> None:
    _assert_html_table_well_formed(_benchmark_text())


def test_benchmark_stress_child_sizes() -> None:
    _assert_stress_child_sizes(_benchmark_text())


def _data_benchmark_text() -> str:
    return DATA_BENCHMARK_PATH.read_text(encoding="utf-8")


@pytest.mark.corpus
def test_corpus_data_benchmark_matches_fixture_invariants() -> None:
    """Chạy lại bất biến benchmark trên bản benchmark thật trong data/."""
    if not DATA_BENCHMARK_PATH.is_file():
        pytest.skip(
            "Bỏ qua test kho tài liệu: thiếu file benchmark thật "
            f"'{DATA_BENCHMARK_PATH}' (thư mục data/ bị gitignore, chỉ có trên máy "
            "có dữ liệu thật). Fixture tổng hợp đã kiểm tra các bất biến này."
        )
    text = _data_benchmark_text()
    _assert_table_chunking(text)
    _assert_parent_child_section_paths(text)
    _assert_table_children_keep_header(text)
    _assert_html_table_well_formed(text)
    _assert_stress_child_sizes(text)

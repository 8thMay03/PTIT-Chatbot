"""Bất biến bảo toàn hàng bảng (S-02, phục vụ AC-02/AC-03).

Mọi hàng bảng còn lại sau ``clean_text`` phải xuất hiện nguyên vẹn trong ít
nhất một child, không child nào chứa hàng bị cắt dở, và mọi child chứa hàng
dữ liệu đều phải chứa header của bảng đó.
"""

from pathlib import Path

import pytest

from app.core.config import settings
from app.ingestion.chunker import find_table_coverage_issues, split_parent_child
from app.ingestion.cleaner import clean_text

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "corpus"
BENCHMARK = (FIXTURE_DIR / "chunker-tables-benchmark.md").read_text(encoding="utf-8")
COMPACT = (FIXTURE_DIR / "chunker-tables-llamaparse-compact.md").read_text(encoding="utf-8")

LONG_MD_TABLE = "\n".join(
    [
        "## Giao dịch",
        "",
        "| Mã | Ngày | Số tiền |",
        "| --- | --- | --- |",
        *(
            f"| TX-{index:03d} | 2026-01-{index:02d} | {(1000 + index) * 1000} |"
            for index in range(1, 121)
        ),
    ]
)

# Một hàng rất dài phải giữ nguyên vẹn, không cắt giữa hàng.
VERY_LONG_ROW_TABLE = "\n".join(
    [
        "## Chính sách",
        "",
        "| Quy tắc | Mô tả |",
        "| --- | --- |",
        f"| A | {'chi tiết quan trọng ' * 120}|",
        "| B | ngắn |",
    ]
)

# Bảng ngắt trang có lặp lại header: mỗi khối tự tách với header riêng,
# bất biến vẫn phải giữ (gộp khối là việc của S-03).
REPEATED_HEADER_PAGES = "\n".join(
    [
        "## Kế hoạch",
        "",
        "| TT | Môn | TC |",
        "| --- | --- | --- |",
        "| 1 | Toán | 2 |",
        "| 2 | Lý | 2 |",
        "",
        "| TT | Môn | TC |",
        "| --- | --- | --- |",
        "| 3 | Hóa | 2 |",
        "| 4 | Văn | 2 |",
    ]
)

HTML_TABLE = "\n".join(
    [
        "## Báo cáo",
        "",
        "<table>",
        "  <thead>",
        "    <tr><th>Mã</th><th>Giá trị</th></tr>",
        "  </thead>",
        "  <tbody>",
        *(f"    <tr><td>RPT-{index:03d}</td><td>{index * 10}</td></tr>" for index in range(1, 31)),
        "  </tbody>",
        "</table>",
    ]
)


def _children(text: str) -> list[str]:
    return [
        chunk.text
        for chunk in split_parent_child(
            text,
            parent_size=2048,
            parent_overlap=256,
            child_size=1024,
            child_overlap=128,
            min_child_size=120,
        )
    ]


@pytest.mark.parametrize(
    "text",
    [BENCHMARK, COMPACT, LONG_MD_TABLE, VERY_LONG_ROW_TABLE, REPEATED_HEADER_PAGES, HTML_TABLE],
    ids=["benchmark", "compact", "long-table", "very-long-row", "repeated-header", "html"],
)
def test_table_rows_survive_chunking(text: str) -> None:
    issues = find_table_coverage_issues(clean_text(text), _children(text))

    assert issues == [], [(issue.kind, issue.child_index, issue.excerpt) for issue in issues]


def test_coverage_issue_excerpt_is_bounded() -> None:
    row = "| " + "x" * 500 + " |"
    text = "## T\n\n| A |\n| --- |\n" + row
    issues = find_table_coverage_issues(clean_text(text), ["không có hàng nào"])
    assert issues
    assert all(len(issue.excerpt) <= 120 for issue in issues)
    assert all(issue.child_index == -1 for issue in issues if issue.kind == "missing")


def test_data_file_d26_has_no_table_coverage_issues() -> None:
    candidates = list(Path(settings.documents_path).rglob("*.md"))
    if not candidates:
        pytest.skip("Thiếu file dữ liệu D26 trong data/ (thư mục bị gitignore).")
    text = max(candidates, key=lambda path: path.stat().st_size).read_text(encoding="utf-8")
    issues = find_table_coverage_issues(clean_text(text), _children(text))

    assert issues == [], [(issue.kind, issue.child_index, issue.excerpt) for issue in issues[:10]]

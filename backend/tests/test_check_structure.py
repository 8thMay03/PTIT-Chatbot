from pathlib import Path

from app.parsers.normalize import normalize_markdown
from scripts.check_structure import analyze, articles_without_chapter, format_tree, main

FIXTURES = Path(__file__).parent / "fixtures" / "corpus" / "heading-normalization"


def _codes(markdown: str, **options) -> list[str]:
    return [finding.code for finding in analyze(markdown, **options).findings]


def test_normalized_fixture_has_no_errors():
    report = analyze(normalize_markdown((FIXTURES / "bold-md.md").read_text(encoding="utf-8")))

    assert report.errors == []
    # "Điều 8" after "Điều 5" in the excerpt is reported as a warning only.
    assert {finding.code for finding in report.findings} <= {"article_numbering"}


def test_raw_bold_markdown_reports_articles_that_are_not_headings():
    raw = (FIXTURES / "bold-md.md").read_text(encoding="utf-8")

    codes = _codes(raw)

    assert "article_not_heading" in codes
    assert "multiple_articles" in codes


def test_article_without_title_and_missing_chapter():
    markdown = (
        "## QUY ĐỊNH A\n\n### Chương I: CHUNG\n\n##### Điều 1. Một\n\nx\n\n"
        "### Ghi chú\n\n##### Điều 2. Hai\n\ny\n\n"
        "# PHẦN II: KHÁC\n\n##### Điều 3. Ba\n\nz\n"
    )

    report = analyze(markdown)
    codes = [finding.code for finding in report.findings]

    assert codes.count("article_without_chapter") == 1
    assert codes.count("article_without_title") == 1
    assert [section.heading.title for section in articles_without_chapter(report)] == ["Điều 2. Hai", "Điều 3. Ba"]


def test_article_numbering_gaps_are_warnings():
    report = analyze("## QUY ĐỊNH A\n\n##### Điều 1. Một\n\nx\n\n##### Điều 4. Bốn\n\ny\n")

    assert [finding.code for finding in report.findings] == ["article_numbering"]
    assert report.errors == []


def test_long_sections_use_the_threshold():
    markdown = "## QUY ĐỊNH A\n\n" + "chữ " * 100

    assert "long_section" in _codes(markdown, max_section_chars=100)
    assert "long_section" not in _codes(markdown, max_section_chars=10_000)


def test_study_plan_checks():
    markdown = (
        "## KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN\n\n#### NĂM HỌC THỨ NHẤT\n\nx\n\n"
        "## KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN NGÀNH KẾ TOÁN KHÓA 2026\n\n#### NĂM HỌC THỨ HAI\n\ny\n"
    )

    codes = _codes(markdown)

    assert codes.count("program_without_name") == 1
    assert "plan_outside_program" not in codes


def test_tree_lists_levels_and_kinds():
    report = analyze("## QUY ĐỊNH A\n\n### Chương I: CHUNG\n\n##### Điều 1. Một\n\nnội dung\n")

    tree = format_tree(report)

    assert [line.split(" [")[0] for line in tree] == [
        "     1    QUY ĐỊNH A",
        "     3      Chương I: CHUNG",
        "     5          Điều 1. Một",
    ]
    assert [line.split(" [")[1].split(",")[0] for line in tree] == ["title", "chapter", "article"]


def test_cli_strict_exit_code(tmp_path, capsys):
    good = tmp_path / "good.md"
    good.write_text("**QUY ĐỊNH A**\n\n**Điều 1. Một**\n\nx\n", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text("# QUY ĐỊNH A\n\n- Điều 1. Một\n\nĐiều 2. Hai là một câu rất dài " + "x" * 300 + "\n", encoding="utf-8")

    assert main([str(good), "--strict"]) == 0
    assert main([str(bad), "--strict"]) == 1
    assert main([str(bad)]) == 0
    assert "article_not_heading" in capsys.readouterr().out

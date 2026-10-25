"""Kiểm tra cấu trúc heading của một tài liệu sau bước chuẩn hóa Markdown.

Đọc tài liệu qua đúng đường ingest (`read_document_text`, gồm `normalize_markdown`),
in cây heading và cảnh báo các bất thường làm hỏng chunking/citation:

- ``article_not_heading`` (lỗi): dòng thân bài bắt đầu bằng "Điều N." mà không phải heading.
- ``multiple_articles`` (lỗi): một section chứa từ 2 Điều trở lên.
- ``article_without_title`` (lỗi): đường dẫn của Điều thiếu tiêu đề văn bản (cấp 2).
- ``article_without_chapter`` (lỗi): quy định đã có Chương phía trên nhưng Điều không nằm
  trong Chương nào.
- ``program_without_name`` (lỗi): heading "KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN" thiếu tên ngành.
- ``plan_outside_program`` (lỗi): section thuộc kế hoạch học tập (năm học, chuyên ngành,
  học phần tự chọn…) không nằm dưới heading ngành.
- ``long_section`` (cảnh báo): section dài hơn ngưỡng ký tự.
- ``article_numbering`` (cảnh báo): số Điều nhảy cóc hoặc lặp trong cùng quy định — văn
  bản "lược trích" thường nhảy số nên chỉ cảnh báo.

Ví dụ::

    python -m scripts.check_structure "..\\data\\processed\\Sổ tay sinh viên D26 _1_ _1_.md" --tree
    python -m scripts.check_structure "..\\data\\raw\\Sổ tay sinh viên D26.pdf" --parser docling --strict
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from app.ingestion.chunker import _parse_heading
from app.parsers.normalize import classify_heading

ERROR_CODES = frozenset(
    {
        "article_not_heading",
        "multiple_articles",
        "article_without_title",
        "article_without_chapter",
        "program_without_name",
        "plan_outside_program",
    }
)
DEFAULT_MAX_SECTION_CHARS = 10_000

_ARTICLE_LINE = re.compile(r"^\s*(?:\*\*|__)?\s*(?:…|\.{3})?\s*điều\s+(\d+)\s*[.:]", re.IGNORECASE)
_ARTICLE_NUMBER = re.compile(r"^điều\s+(\d+)", re.IGNORECASE)
_PROGRAM_PHRASE = re.compile(r"KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN", re.IGNORECASE)
_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class Heading:
    line: int
    level: int
    title: str
    kind: str


@dataclass
class Section:
    heading: Heading | None
    path: tuple[Heading, ...]
    chars: int = 0
    in_program: bool = False
    body_articles: list[tuple[int, str]] = field(default_factory=list)


@dataclass(frozen=True)
class Finding:
    code: str
    line: int
    message: str

    @property
    def is_error(self) -> bool:
        return self.code in ERROR_CODES


@dataclass
class StructureReport:
    sections: list[Section]
    findings: list[Finding]

    @property
    def headings(self) -> list[Heading]:
        return [section.heading for section in self.sections if section.heading is not None]

    @property
    def errors(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.is_error]

    def counts(self) -> Counter:
        return Counter(finding.code for finding in self.findings)


def split_sections(markdown: str) -> list[Section]:
    """Walk headings like the chunker does and keep line numbers and heading kinds."""
    sections: list[Section] = [Section(heading=None, path=())]
    stack: list[Heading] = []
    in_program = False
    in_fence = False

    for line_no, line in enumerate(markdown.splitlines(), start=1):
        if _FENCE.match(line):
            in_fence = not in_fence
        parsed = None if in_fence else _parse_heading(line)
        if parsed is None:
            current = sections[-1]
            current.chars += len(line) + 1
            article = None if in_fence else _ARTICLE_LINE.match(line)
            if article:
                current.body_articles.append((line_no, line.strip()))
            continue

        level, title = parsed
        kind = classify_heading(title, in_program=in_program)
        if kind == "program":
            in_program = True
        elif kind in ("part", "title"):
            in_program = False
        heading = Heading(line=line_no, level=level, title=title, kind=kind)
        stack = [item for item in stack if item.level < level] + [heading]
        sections.append(Section(heading=heading, path=tuple(stack), chars=len(line) + 1, in_program=in_program))

    return [section for section in sections if section.heading is not None or section.chars > 1]


def analyze(markdown: str, *, max_section_chars: int = DEFAULT_MAX_SECTION_CHARS) -> StructureReport:
    sections = split_sections(markdown)
    findings: list[Finding] = []
    # Last article number and whether a Chương was seen, per regulation title heading line.
    last_article: dict[int, int] = {}
    titles_with_chapter: set[int] = set()

    for section in sections:
        heading = section.heading
        line = heading.line if heading else 1
        label = heading.title if heading else "(đầu tài liệu)"

        if section.chars > max_section_chars:
            findings.append(Finding("long_section", line, f"{label!r}: {section.chars} ký tự"))

        for body_line, text in section.body_articles:
            findings.append(Finding("article_not_heading", body_line, text[:120]))
        article_count = len(section.body_articles) + (1 if heading and heading.kind == "article" else 0)
        if article_count >= 2:
            findings.append(Finding("multiple_articles", line, f"{label!r} chứa {article_count} Điều"))

        if heading is None:
            continue
        title = _nearest(section.path, "title")
        if heading.kind == "chapter" and title is not None:
            titles_with_chapter.add(title.line)

        if heading.kind == "article":
            if title is None:
                findings.append(Finding("article_without_title", line, f"{label!r}: {_path_text(section.path)}"))
            else:
                if title.line in titles_with_chapter and _nearest(section.path, "chapter") is None:
                    findings.append(
                        Finding("article_without_chapter", line, f"{label!r}: {_path_text(section.path)}")
                    )
                number = _article_number(heading.title)
                previous = last_article.get(title.line)
                if number is not None:
                    if previous is not None and number != previous + 1:
                        findings.append(
                            Finding("article_numbering", line, f"Điều {previous} → Điều {number} trong {title.title!r}")
                        )
                    last_article[title.line] = number

        if heading.kind == "program" and not _PROGRAM_PHRASE.sub("", heading.title).strip(" -–:"):
            findings.append(Finding("program_without_name", line, label))
        if section.in_program and heading.kind != "program":
            if _nearest(section.path, "program") is None:
                findings.append(Finding("plan_outside_program", line, f"{label!r}: {_path_text(section.path)}"))

    findings.sort(key=lambda finding: (finding.line, finding.code))
    return StructureReport(sections=sections, findings=findings)


def articles_without_chapter(report: StructureReport) -> list[Section]:
    """Articles allowed to sit directly under their title (excerpted regulations)."""
    return [
        section
        for section in report.sections
        if section.heading is not None
        and section.heading.kind == "article"
        and _nearest(section.path, "chapter") is None
    ]


def _nearest(path: tuple[Heading, ...], kind: str) -> Heading | None:
    for item in reversed(path[:-1]):
        if item.kind == kind:
            return item
    return None


def _article_number(title: str) -> int | None:
    match = _ARTICLE_NUMBER.match(title)
    return int(match.group(1)) if match else None


def _path_text(path: tuple[Heading, ...]) -> str:
    return " > ".join(item.title for item in path)


def format_tree(report: StructureReport, *, max_title: int = 110) -> list[str]:
    lines = []
    for section in report.sections:
        heading = section.heading
        if heading is None:
            lines.append(f"{'':>6}  (đầu tài liệu) [{section.chars}]")
            continue
        title = heading.title if len(heading.title) <= max_title else heading.title[: max_title - 1] + "…"
        indent = "  " * (heading.level - 1)
        lines.append(f"{heading.line:>6}  {indent}{title} [{heading.kind}, {section.chars}]")
    return lines


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="In cây heading và cảnh báo cấu trúc tài liệu sau chuẩn hóa.")
    parser.add_argument("path", type=Path, help="Tài liệu nguồn (.md/.txt/.pdf/.docx).")
    parser.add_argument("--parser", dest="parser_name", help="Tên parser (mặc định theo đuôi file), vd. docling.")
    parser.add_argument("--tree", action="store_true", help="In cây heading kèm loại và số ký tự từng section.")
    parser.add_argument(
        "--max-section-chars",
        type=int,
        default=DEFAULT_MAX_SECTION_CHARS,
        help=f"Ngưỡng cảnh báo section quá dài (mặc định {DEFAULT_MAX_SECTION_CHARS}).",
    )
    parser.add_argument("--strict", action="store_true", help="Trả exit code 1 khi có lỗi cứng.")
    parser.add_argument("--limit", type=int, default=50, help="Số dòng tối đa in cho mỗi loại cảnh báo.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from app.parsers import DocumentParseError, read_document_text

    try:
        # convert=False: Docling chỉ đọc cache, không chạy chuyển đổi tốn thời gian.
        text = read_document_text(args.path, convert=False, parser_name=args.parser_name)
    except (DocumentParseError, OSError) as exc:
        print(f"Không đọc được {args.path}: {exc}", file=sys.stderr)
        return 2
    if text is None:
        print(f"{args.path} chưa có bản chuyển đổi trong cache; hãy ingest/preview trước.", file=sys.stderr)
        return 2

    report = analyze(text, max_section_chars=args.max_section_chars)
    if args.tree:
        print("\n".join(format_tree(report)))
        print()

    by_code: dict[str, list[Finding]] = {}
    for finding in report.findings:
        by_code.setdefault(finding.code, []).append(finding)
    for code, items in by_code.items():
        severity = "LỖI" if code in ERROR_CODES else "cảnh báo"
        print(f"[{severity}] {code}: {len(items)}")
        for finding in items[: args.limit]:
            print(f"  dòng {finding.line}: {finding.message}")
        if len(items) > args.limit:
            print(f"  … còn {len(items) - args.limit} mục")

    headings = report.headings
    kinds = Counter(heading.kind for heading in headings)
    free_articles = articles_without_chapter(report)
    print(
        f"\nTóm tắt: {len(headings)} heading ({', '.join(f'{k}={v}' for k, v in sorted(kinds.items()))}); "
        f"{len(report.errors)} lỗi, {len(report.findings) - len(report.errors)} cảnh báo; "
        f"{len(free_articles)} Điều không có Chương (hợp lệ khi quy định không có Chương phía trên)."
    )
    return 1 if args.strict and report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

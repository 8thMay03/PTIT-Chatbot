"""Trích Điều/Khoản/Điểm của một đoạn văn bản theo cấu trúc (RAG-22).

Khoản/Điểm chỉ có nghĩa bên trong một Điều: danh sách ``1.``/``a)`` ở mục không phải
Điều (các bước thủ tục, danh mục trong Sổ tay) không phải Khoản/Điểm. Chunker gọi hàm
này lần lượt cho các chunk của cùng một section và truyền ``last_clause`` sang chunk kế
tiếp, để chunk bắt đầu giữa Khoản (chỉ chứa ``b)``, ``c)``) vẫn biết mình thuộc Khoản nào.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MAX_UNITS = 12
ARTICLE_SCAN_LINES = 8

_ARTICLE_RE = re.compile(r"\bĐiều\s+\d+[a-zA-Z]?\s*[.:]?\s*[^>]{0,220}", re.IGNORECASE)
_MARKER_PREFIX = r"^\s*(?:[-*]\s*)?(?:\*\*)?"
# Khoản chỉ dạng "1." (văn bản pháp quy); "1)" chỉ gặp ở danh sách thường trên kho hiện có.
_CLAUSE_RE = re.compile(_MARKER_PREFIX + r"(\d{1,2})\.\s+")
_POINT_RE = re.compile(_MARKER_PREFIX + r"([a-zđ])[.)]\s+")
# Dòng mở một Điều mới trong thân (ví dụ "**Điều 7.** ..." không phải heading markdown).
_BODY_ARTICLE_RE = re.compile(r"^\s*(?:[-*]\s+)?(?:\*\*|__)?\s*Điều\s+\d+[a-zA-Z]?\b", re.IGNORECASE)
_MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
_HTML_TABLE_START_RE = re.compile(r"<table\b", re.IGNORECASE)
_HTML_TABLE_END_RE = re.compile(r"</table\s*>", re.IGNORECASE)


@dataclass(frozen=True)
class LegalUnits:
    article: str | None = None
    clauses: list[str] = field(default_factory=list)
    points: list[str] = field(default_factory=list)
    # Khoản đang mở ở cuối đoạn, để chunk kế tiếp của cùng section kế thừa.
    last_clause: str | None = None


def extract_article(heading: str, section_path: str, text: str) -> str | None:
    """Điều của đoạn: heading, rồi các phần của section_path, rồi vài dòng đầu text."""

    for candidate in (heading, section_path, *text.splitlines()[:ARTICLE_SCAN_LINES]):
        match = _ARTICLE_RE.search(clean_legal_text(candidate))
        if match:
            return match.group(0).strip(" .:")
    return None


def extract_legal_units(
    heading: str,
    section_path: str,
    text: str,
    open_clause: str | None = None,
) -> LegalUnits:
    """Điều/Khoản/Điểm của ``text``; không có Điều thì không có Khoản/Điểm.

    ``open_clause`` là Khoản đang mở ở cuối chunk trước của cùng section. Nó được tính
    là Khoản của ``text`` khi dấu mốc đầu tiên trong text là một Điểm, hoặc text không
    có dấu mốc nào (đoạn tiếp nối của Khoản đó).
    """

    article = extract_article(heading, section_path, text)
    if not article:
        return LegalUnits()

    clauses: list[str] = []
    points: list[str] = []
    current = open_clause
    first_marker: str | None = None
    for line in _body_lines(text):
        if _BODY_ARTICLE_RE.match(line):
            first_marker = first_marker or "article"
            current = None
            continue
        clause = _CLAUSE_RE.match(line)
        if clause:
            first_marker = first_marker or "clause"
            current = clause.group(1)
            _append_unique(clauses, current)
            continue
        point = _POINT_RE.match(line)
        if point:
            if first_marker is None and open_clause:
                _append_unique(clauses, open_clause)
            first_marker = first_marker or "point"
            _append_unique(points, point.group(1).casefold())

    if first_marker is None and open_clause:
        clauses = [open_clause]
    return LegalUnits(
        article=article,
        clauses=clauses[:MAX_UNITS],
        points=points[:MAX_UNITS],
        last_clause=current,
    )


def clean_legal_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[#*_`]+", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _body_lines(text: str) -> list[str]:
    """Các dòng có thể chứa dấu mốc: bỏ heading markdown, dòng bảng markdown và bảng HTML."""

    lines: list[str] = []
    in_html_table = False
    for line in text.splitlines():
        if in_html_table or _HTML_TABLE_START_RE.search(line):
            in_html_table = not _HTML_TABLE_END_RE.search(line)
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("|") or _MARKDOWN_HEADING_RE.match(line):
            continue
        lines.append(line)
    return lines


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)

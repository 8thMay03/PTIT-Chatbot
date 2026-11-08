"""Trích Điều/Khoản/Điểm của một đoạn văn bản theo cấu trúc (RAG-22).

Khoản/Điểm chỉ có nghĩa bên trong một Điều: danh sách ``1.``/``a)`` ở mục không phải
Điều (các bước thủ tục, danh mục trong Sổ tay) không phải Khoản/Điểm. Chunker gọi hàm
này lần lượt cho các chunk của cùng một section và truyền ``last_clause`` sang chunk kế
tiếp, để chunk bắt đầu giữa Khoản (chỉ chứa ``b)``, ``c)``) vẫn biết mình thuộc Khoản nào.

Khoản là dòng bắt đầu bằng ``N.``, hoặc ``N.`` giữa dòng sau dấu kết câu và trước chữ hoa
khi N đúng là số kế tiếp (bản parse hay gộp nhiều Khoản vào một đoạn). Điểm là dòng bắt
đầu bằng ``a)``/``a.``. Dòng bảng (markdown/HTML) và heading markdown bị bỏ qua.
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
# Khoản giữa dòng: sau dấu kết câu, số rồi chữ hoa ("... Hội đồng. 5. Hai tuần ...").
_INLINE_CLAUSE_RE = re.compile(r"(?<=[.;:!?])\s+(\d{1,2})\.\s+(?=(\S))")
_BODY_ARTICLE_RE = re.compile(r"^\s*(?:[-*]\s+)?(?:\*\*|__)?\s*Điều\s+\d+[a-zA-Z]?\b", re.IGNORECASE)
_MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
_HTML_TABLE_START_RE = re.compile(r"<table\b", re.IGNORECASE)
_HTML_TABLE_END_RE = re.compile(r"</table\s*>", re.IGNORECASE)
# Khóa metadata chunk/context. Có khóa ``legal_clauses`` (kể cả rỗng) = giá trị tính lúc
# chunking; không có = chunk cũ, citation tự tính lại (không kế thừa Khoản).
LEGAL_METADATA_KEYS = ("legal_article", "legal_clauses", "legal_points")


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

    ``open_clause`` là Khoản đang mở ở cuối chunk trước của cùng section; nó là Khoản
    của ``text`` khi text có nội dung (đoạn văn hoặc Điểm) đứng trước dấu Khoản đầu tiên.
    Khoản giữa dòng ("... Hội đồng. 5. Hai tuần ...", bản parse hay gộp các Khoản vào một
    đoạn) chỉ được nhận khi đúng số kế tiếp Khoản đang mở; số khác thì không còn biết
    Khoản đang mở nên không kế thừa tiếp, thay vì gắn nhầm Khoản.
    """

    article = extract_article(heading, section_path, text)
    if not article:
        return LegalUnits()

    clauses: list[str] = []
    points: list[str] = []
    current = open_clause
    pending_inherit = open_clause is not None
    inherited = first_clause_seen = False
    for kind, value in _marker_events(text):
        if kind == "article":
            current, pending_inherit = None, False
            continue
        if kind in ("text", "point"):
            if pending_inherit:
                _append_unique(clauses, open_clause)
                pending_inherit, inherited = False, True
            if kind == "point":
                _append_unique(points, value)
            continue
        if not first_clause_seen:
            first_clause_seen = True
            # Đánh số bắt đầu lại (dấu Khoản đầu tiên không lớn hơn Khoản kế thừa): phần
            # đứng trước là một mục khác, không phải phần tiếp của Khoản đang mở.
            if inherited and int(value) <= int(open_clause):
                clauses.remove(open_clause)
                current = None
        pending_inherit = False
        if kind == "inline_clause" and int(value) != int(current or 0) + 1:
            current = None
        else:
            current = value
            _append_unique(clauses, value)

    return LegalUnits(
        article=article,
        clauses=clauses[:MAX_UNITS],
        points=points[:MAX_UNITS],
        last_clause=current,
    )


def legal_metadata(chunk: object) -> dict:
    """Khóa ``legal_*`` để ghi vào metadata chunk (Chunk hoặc ParentChildChunk)."""

    return {
        "legal_article": getattr(chunk, "legal_article", None),
        "legal_clauses": list(getattr(chunk, "legal_clauses", ())),
        "legal_points": list(getattr(chunk, "legal_points", ())),
    }


def copy_legal_metadata(metadata: dict, target: dict) -> dict:
    """Chép các khóa ``legal_*`` có trong ``metadata`` sang ``target``; không có thì bỏ qua."""

    for key in LEGAL_METADATA_KEYS:
        if key in metadata:
            target[key] = metadata[key]
    return target


def clean_legal_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[#*_`]+", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _marker_events(text: str) -> list[tuple[str, str]]:
    """Dãy dấu mốc theo thứ tự: ``article``, ``clause``, ``inline_clause``, ``point``, ``text``."""

    events: list[tuple[str, str]] = []
    for line in _body_lines(text):
        if _BODY_ARTICLE_RE.match(line):
            events.append(("article", ""))
            continue
        clause = _CLAUSE_RE.match(line)
        point = None if clause else _POINT_RE.match(line)
        if clause:
            events.append(("clause", clause.group(1)))
        elif point:
            events.append(("point", point.group(1).casefold()))
        else:
            events.append(("text", ""))
        rest = (clause or point).end() if clause or point else 0
        for inline in _INLINE_CLAUSE_RE.finditer(line, rest):
            if inline.group(2).isupper():
                events.append(("inline_clause", inline.group(1)))
    return events


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

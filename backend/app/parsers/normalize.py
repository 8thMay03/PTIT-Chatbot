"""Normalize parser output into one Markdown shape: Unicode, escapes and heading hierarchy.

Every parser's output passes through ``normalize_markdown`` so the chunker sees the same
structure whether headings came from Docling (all ``##``) or from bold paragraphs in a
hand-made Markdown export. Regulation headings get fixed levels:

    PHẦN → 1, document title (QUY ĐỊNH/QUY CHẾ/HƯỚNG DẪN/PHỤ LỤC…) → 2, Chương → 3,
    Mục → 4, Điều → 5

and any other heading is placed under the nearest structural heading above it. Inside a
study plan ("KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN …") the program heading is level 2,
CHUYÊN NGÀNH 3 and NĂM HỌC/HỌC KỲ 4, so every year sits under its program name.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_MAX_LEVEL = 6
# Longest plain (non-heading, non-bold) line that may be promoted to a structural heading.
_MAX_PLAIN_HEADING = 200
_MAX_BOLD_HEADING = 150

_STRUCTURAL_LEVELS = {
    "part": 1,
    "title": 2,
    "program": 2,
    "chapter": 3,
    "major": 3,
    "section": 4,
    "year": 4,
    "article": 5,
}

_ROMAN = r"(?-i:[IVXLC]+)"
_PART = re.compile(r"^PHẦN\s+(?:[IVXLC]+|\d+)\b")
_CHAPTER = re.compile(rf"^chương\s+(?:{_ROMAN}|\d+)\b", re.IGNORECASE)
_SECTION = re.compile(rf"^mục\s+(?:\d+|{_ROMAN})\b", re.IGNORECASE)
_ARTICLE = re.compile(r"^điều\s+\d+\s*[.:]", re.IGNORECASE)
_LABEL = re.compile(rf"^(?P<label>PHẦN|chương|mục)\s+(?P<number>{_ROMAN}|\d+)\b\s*[:.\-–]?\s*(?P<rest>.*)$", re.IGNORECASE)
_TITLE = re.compile(
    r"^(?:[IVX]+\s*[/.)]\s*)?"
    r"(?:QUY ĐỊNH|QUY CHẾ|HƯỚNG DẪN|NGHỊ ĐỊNH|THÔNG TƯ|QUYẾT ĐỊNH|PHỤ LỤC|Phụ lục"
    r"|(?:Nghị định|Thông tư|Quyết định)\s+số)\b"
)
_PROGRAM = re.compile(r"KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN", re.IGNORECASE)
_BARE_PROGRAM = re.compile(r"^KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN$", re.IGNORECASE)
_PROGRAM_NAME = re.compile(r"^(?:NGÀNH|CHƯƠNG TRÌNH)\b", re.IGNORECASE)
# OCR/typing variants of "CHUYÊN NGÀNH" all occur in the handbook.
_MAJOR = re.compile(r"^CHUY[ÊỂẾỆE]N\s+NGÀNH\b", re.IGNORECASE)
_YEAR = re.compile(r"^(?:NĂM\s+(?:HỌC\s+)?THỨ|HỌC\s+KỲ)\s+\S", re.IGNORECASE)
_GLUED_ARTICLE = re.compile(r"^(?P<head>.*\S)\s+(?P<article>điều\s+\d+\s*[.:].*)$", re.IGNORECASE)
# "II/ Quyết định số 05/2022/QĐ-TTg …" opens an excerpted legal text even as a plain line.
_DECREE = re.compile(r"^[IVX]+\s*/\s*(?:Nghị định|Quyết định|Thông tư)\s+số\b", re.IGNORECASE)
_APPENDIX = re.compile(r"^(?:PHỤ LỤC|Phụ lục)\s+(?:\d+|[IVX]+)\b")
_NUMBERED = re.compile(r"^(?:\d|[IVXLC]+[.)/]|[a-zđ][.)]|[-–(])")
_TOC = re.compile(r"^MỤC LỤC$", re.IGNORECASE)
_TOC_PAGE = re.compile(r"\s\d{1,3}$")

_ATX = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
_BOLD_LINE = re.compile(r"^\*\*([^*\n]{2,200}?)\*\*[ \t]*:?[ \t]*$")
_FENCE = re.compile(r"^(```|~~~)")
_HTML_TABLE_START = re.compile(r"<table\b", re.IGNORECASE)
_HTML_TABLE_END = re.compile(r"</table\s*>", re.IGNORECASE)
_LIST_MARKER = re.compile(r"^(?:[-+*]\s|\d+[.)]\s|[a-zđ][.)]\s)")
_ESCAPED_UNDERSCORE = re.compile(r"\\_")


@dataclass
class _Line:
    raw: str
    # Cleaned heading title when this line is (or is promoted to) a heading.
    heading: str | None = None
    # Original ATX level; None for promoted bold/plain lines.
    source_level: int | None = None
    # Cleaned text when the line may continue a bare "PHẦN IV" / "Chương II" label.
    continuation: str | None = None
    # Promoted bold label ending with ":" ("Lãnh đạo phòng:") introduces the text below it.
    introduces: bool = False
    dropped: bool = False


def normalize_markdown(text: str) -> str:
    """Return text with NFC, unescaped entities and a consistent heading hierarchy."""
    # PDF text layers often carry decomposed Vietnamese diacritics; NFC keeps BM25 and
    # embeddings consistent with user queries.
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n")
    # Docling escapes "&" ("CT&amp;CTSV") and "_"; "<"/">" stay escaped so they never look like HTML.
    text = text.replace("&amp;", "&")
    text = _ESCAPED_UNDERSCORE.sub("_", text)

    lines = _scan(text.split("\n"))
    _merge_bare_labels(lines)
    lines = _split_glued_articles(lines)
    _merge_program_names(lines)
    _demote_toc_entries(lines)
    return "\n".join(_render(lines))


def classify_heading(title: str, *, in_program: bool = False) -> str:
    """Return the structural kind of a cleaned heading title, or "other"."""
    if _PART.match(title):
        return "part"
    if _ARTICLE.match(title):
        return "article"
    if _CHAPTER.match(title):
        return "chapter"
    if _SECTION.match(title):
        return "section"
    if _PROGRAM.search(title):
        return "program"
    if _TITLE.match(title) or _DECREE.match(title):
        return "title"
    if in_program:
        if _MAJOR.match(title):
            return "major"
        if _YEAR.match(title):
            return "year"
    return "other"


def _scan(raw_lines: list[str]) -> list[_Line]:
    lines: list[_Line] = []
    in_fence = False
    in_table = False
    for raw in raw_lines:
        stripped = raw.strip()
        if _FENCE.match(stripped):
            in_fence = not in_fence
            lines.append(_Line(raw))
            continue
        if in_fence:
            lines.append(_Line(raw))
            continue
        if in_table:
            in_table = not _HTML_TABLE_END.search(stripped)
            lines.append(_Line(raw))
            continue
        start = _HTML_TABLE_START.search(stripped)
        if start:
            in_table = not _HTML_TABLE_END.search(stripped, start.end())
            lines.append(_Line(raw))
            continue
        if not stripped or stripped.startswith("|"):
            lines.append(_Line(raw))
            continue

        atx = _ATX.match(raw)
        if atx:
            title = _clean_title(atx.group(2))
            if title:
                lines.append(_Line(raw, heading=title, source_level=len(atx.group(1)), continuation=title))
            else:
                lines.append(_Line(raw))
            continue

        bold = _BOLD_LINE.match(stripped)
        if bold:
            title = _clean_title(bold.group(1))
            heading = title if _promotes_bold(title) else None
            introduces = stripped.rstrip("*").rstrip().endswith(":")
            lines.append(_Line(raw, heading=heading, continuation=title or None, introduces=introduces))
            continue

        if _DECREE.match(stripped):
            lines.append(_Line(raw, heading=_clean_title(stripped)))
            continue

        if len(stripped) <= _MAX_PLAIN_HEADING and not _LIST_MARKER.match(stripped):
            title = _clean_title(stripped)
            heading = title if _promotes_plain(title) else None
            continuation = title if _looks_like_title_line(title) else None
            lines.append(_Line(raw, heading=heading, continuation=continuation))
            continue

        lines.append(_Line(raw))
    return lines


def _clean_title(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    # Drop emphasis markers but keep footnote marks such as "(*)" and "(**)".
    value = re.sub(r"`+|(?<!\()\*+(?!\))", "", value)
    value = re.sub(r"\s+", " ", value).strip(" #")
    # Docling sometimes keeps a leading ellipsis from the previous page ("…Điều 2.").
    value = re.sub(r"^(?:…|\.{3})\s*", "", value)
    return value.rstrip(":").strip()


def _has_letter(value: str) -> bool:
    return any(char.isalpha() for char in value)


def _promotes_bold(title: str) -> bool:
    """Promote whole-line bold text unless it reads as a sentence or a bare number."""
    if not _has_letter(title) or len(title) > _MAX_BOLD_HEADING + 50:
        return False
    if classify_heading(title) in ("part", "article", "chapter", "section"):
        return True
    return len(title) <= _MAX_BOLD_HEADING and not title.endswith((".", ";", ","))


def _promotes_plain(title: str) -> bool:
    """Promote an unformatted line only when it is unmistakably a structural label."""
    if _ARTICLE.match(title) or _APPENDIX.match(title):
        return True
    label = _LABEL.match(title)
    if not label or classify_heading(title) not in ("part", "chapter", "section"):
        return False
    rest = label.group("rest")
    separated = bool(re.match(rf"^\S+\s+\S+\s*[:.\-–]", title))
    # "Chương II của Quy định này …" is body text; "Chương IV KHEN THƯỞNG" is a heading.
    return not rest or separated or rest == rest.upper()


def _looks_like_title_line(title: str) -> bool:
    return _has_letter(title) and len(title) <= _MAX_BOLD_HEADING and title == title.upper()


def _is_bare_label(title: str) -> bool:
    label = _LABEL.match(title)
    return bool(label) and not label.group("rest") and label.group("label").upper() in ("PHẦN", "CHƯƠNG")


def _next_content_index(lines: list[_Line], start: int, *, max_blank: int = 3) -> int | None:
    blanks = 0
    for index in range(start, len(lines)):
        line = lines[index]
        if line.dropped:
            continue
        if not line.raw.strip():
            blanks += 1
            if blanks > max_blank:
                return None
            continue
        return index
    return None


def _merge_bare_labels(lines: list[_Line]) -> None:
    """Join "PHẦN IV" / "Chương VII" with the title on the following line(s)."""
    for index, line in enumerate(lines):
        if line.dropped or line.heading is None or not _is_bare_label(line.heading):
            continue
        is_part = line.heading.upper().startswith("PHẦN")
        parts: list[str] = []
        cursor = index + 1
        while True:
            nxt = _next_content_index(lines, cursor)
            if nxt is None:
                break
            candidate = lines[nxt].continuation
            if candidate is None:
                break
            kind = classify_heading(candidate)
            if kind in ("part", "chapter", "section", "article"):
                break
            # A part label is followed by its own caption, never by the first regulation title;
            # a caption that ends with "," continues on the next line regardless.
            if is_part and kind == "title" and not (parts and parts[-1].endswith((",", "-", "–"))):
                break
            parts.append(candidate)
            lines[nxt].dropped = True
            cursor = nxt + 1
            if not candidate.endswith((",", "-", "–")):
                break
        if parts:
            line.heading = f"{line.heading}: {' '.join(parts)}"


def _split_glued_articles(lines: list[_Line]) -> list[_Line]:
    """Split "Chương V: … Điều 23. …" (Docling layout merge) into two headings."""
    output: list[_Line] = []
    for line in lines:
        if line.heading and not line.dropped and classify_heading(line.heading) in ("chapter", "section"):
            glued = _GLUED_ARTICLE.match(line.heading)
            if glued:
                output.append(_Line(line.raw, heading=glued.group("head"), source_level=line.source_level))
                output.append(_Line(line.raw, heading=glued.group("article"), source_level=line.source_level))
                continue
        output.append(line)
    return output


def _merge_program_names(lines: list[_Line]) -> None:
    """Join a bare "KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN" with the program name below it."""
    for index, line in enumerate(lines):
        if line.dropped or line.heading is None or not _BARE_PROGRAM.match(line.heading):
            continue
        nxt = _next_content_index(lines, index + 1)
        if nxt is None:
            continue
        candidate = lines[nxt].heading or lines[nxt].continuation
        if candidate and _PROGRAM_NAME.match(candidate):
            line.heading = f"{line.heading} {candidate}"
            lines[nxt].dropped = True


def _demote_toc_entries(lines: list[_Line]) -> None:
    """Turn table-of-contents entries ("PHẦN I: … 5") back into plain lines."""
    in_toc = False
    for line in lines:
        if line.dropped or line.heading is None:
            continue
        if _TOC.match(line.heading):
            in_toc = True
            continue
        if not in_toc:
            continue
        if _TOC_PAGE.search(line.heading):
            line.heading = None
            line.source_level = None
        else:
            in_toc = False


def _canonical_title(title: str, kind: str) -> str:
    """Use one separator style for labels: "Chương V : X" / "Chương V - X" → "Chương V: X"."""
    if kind not in ("part", "chapter", "section"):
        return title
    label = _LABEL.match(title)
    if not label:
        return title
    head = f"{label.group('label')} {label.group('number')}"
    rest = label.group("rest").strip()
    return f"{head}: {rest}" if rest else head


def _render(lines: list[_Line]) -> list[str]:
    output: list[str] = []
    anchors: list[int] = []
    # (source level, assigned level) for consecutive non-structural headings.
    others: list[tuple[int, int]] = []
    in_program = False

    for line in lines:
        if line.dropped:
            continue
        if line.heading is None:
            output.append(_strip_atx(line.raw) if line.source_level is None and _ATX.match(line.raw) else line.raw)
            continue

        kind = classify_heading(line.heading, in_program=in_program)
        if kind == "program":
            in_program = True
        elif kind in ("part", "title"):
            in_program = False

        level = _STRUCTURAL_LEVELS.get(kind)
        if level is None and not in_program and anchors and anchors[-1] >= _STRUCTURAL_LEVELS["chapter"]:
            # An all-caps caption after a Chương/Điều ("LỊCH TIẾP SINH VIÊN …") starts a new
            # block of the part; nesting it under the last Điều would hide it in that article.
            if _is_block_caption(line.heading):
                level = _STRUCTURAL_LEVELS["title"]
        if level is not None:
            anchors = [item for item in anchors if item < level] + [level]
            others = []
        else:
            anchor = anchors[-1] if anchors else 0
            # Promoted bold lines carry no level: a label ending with ":" is a child of the
            # previous heading, any other bold line is its sibling.
            if line.source_level is not None:
                source = line.source_level
            elif others:
                source = others[-1][0] + (1 if line.introduces else 0)
            else:
                source = _MAX_LEVEL
            while others and others[-1][0] >= source:
                others.pop()
            level = min(_MAX_LEVEL, (others[-1][1] if others else anchor) + 1)
            others.append((source, level))

        output.append(f"{'#' * level} {_canonical_title(line.heading, kind)}")
    return output


def _is_block_caption(title: str) -> bool:
    return (
        title == title.upper()
        and len(title.split()) >= 3
        and _has_letter(title)
        and not _NUMBERED.match(title)
    )


def _strip_atx(raw: str) -> str:
    return re.sub(r"^\s{0,3}#{1,6}\s+", "", raw)

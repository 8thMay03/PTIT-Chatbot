"""Line-level noise filtering and whitespace normalization before chunking.

``clean_text`` drops lines that are layout artifacts rather than content:

- table-of-contents entries (dot leaders, glued bold page numbers, "MỤC LỤC" body);
- the national title/motto and the "Hà Nội, ngày … tháng … năm …" dateline;
- freestanding page numbers ("- 3 -", "12");
- signature blocks (signer role, "(đã ký)", the signer name, "Nơi nhận" lists).

Lines inside Markdown/HTML tables and fenced code blocks are never touched:
tables are handled by the chunker and code must stay verbatim.
"""

import re

# Form feed / vertical tab split lines via str.splitlines() and break Markdown tables.
_CONTROL_LINE_BREAKS = re.compile(r"[\f\v]+")

_ATX_PREFIX = re.compile(r"^\s{0,3}#{1,6}\s+")
_FENCE = re.compile(r"^(```|~~~)")
_HTML_TABLE_START = re.compile(r"<table\b", re.IGNORECASE)
_HTML_TABLE_END = re.compile(r"</table\s*>", re.IGNORECASE)

# "Lời nói đầu .................. 3", "Mục lục . . . . . 12", "Quy định …… 40"
# hoặc "Quy định tổ chức thi.. 145" (2 chấm + số trang; 2 chấm buộc phải có số
# trang để không ăn nhầm câu kết bằng dấu luyễn).
_TOC_DOT_LEADER = re.compile(
    r"(?:\.{4,}(?:\s*\d{1,4})?|\.{2,}\s*\d{1,4}|(?:\.\s+){3,}\.?\s*\d{0,4}|…{2,}\s*\d{1,4})\s*$"
)
_LEADER_RUN = re.compile(r"(?:\.{2,}|…{2,}|(?:\.\s+){3,}\.?)")
# TOC-entry shapes used to decide how far the "MỤC LỤC" section reaches:
# dot leaders, bold page numbers, or anything ending in a page number.
_TOC_LINE_LIKE = re.compile(
    r"(?:\.{4,}(?:\s*\d{0,4})?|\.{2,}\s*\d{1,4}|…{2,}\s*\d{1,4})\s*$"
    r"|\*\*\s*\d{1,3}\s*\*\*\s*$"
    r"|\s\d{1,3}\s*$"
)
# Whole-line bold ending in a bolded page number: "**PHẦN III: …** **24**"
_BOLD_PAGE_SUFFIX = re.compile(r"\*\*\s*\d{1,3}\s*\*\*\s*$")
# Freestanding page numbers: "- 3 -", "— 12 —", "7"
_PAGE_NUMBER_ONLY = re.compile(r"^[-–—]?\s*\d{1,3}\s*[-–—]?$")
_NATIONAL_TITLE = re.compile(
    r"^cộng\s+ho[àa]\s+x[ãa]\s+h[ộo]i\s+ch[ủu]\s+ngh[ĩi]a\s+vi[ệe]t\s+nam"
    r"(?:\s+đ[ộo]c\s+l[ậa]p\s*[-–]\s*t[ựu]\s*do\s*[-–]\s*h[ạa]nh\s*ph[úu]c)?$",
    re.IGNORECASE,
)
_NATIONAL_MOTTO = re.compile(
    r"^đ[ộo]c\s+l[ậa]p\s*[-–]\s*t[ựu]\s*do\s*[-–]\s*h[ạa]nh\s*ph[úu]c$", re.IGNORECASE
)
# "Hà Nội, ngày 05 tháng 9 năm 2026" — numbers may be missing in parsed PDFs.
_PLACE_DATELINE = re.compile(
    r"^[^,]{1,40},?\s*ng[àa]y\s*\S{0,12}\s*th[áa]ng\s*\S{0,12}\s*n[ăa]m\s*\d{4}\s*$",
    re.IGNORECASE,
)
_SIGNER_ROLE = re.compile(
    r"^(?:(?:trưởng|phó)\s+(?:phòng|ban|đoàn|bộ\s*phận|khoa|viện)"
    r"|giám\s+đốc(?:\s+học\s+viện)?"
    r"|hiệu\s+trưởng"
    r"|tổng\s+giám\s+đốc"
    r"|chủ\s+tịch"
    r"|thư\s+ký"
    r"|quản\s+trị\s+viên)"
    r"[\s.:]*$",
    re.IGNORECASE,
)
_SIGNED_MARK = re.compile(r"^[\(\[]?\s*đ[ãa]\s*k[ýy]\s*[\)\]]?[\s.:]*$", re.IGNORECASE)
_NOI_NHAN = re.compile(r"^n[ơo]i\s+nh[ậa]n\s*:?\s*$", re.IGNORECASE)
# Distribution-list markers: "(b/c)", "(t/h)", "Lưu VT, …"
_DISTRIBUTION_MARKER = re.compile(r"\(\s*[a-zđ]{1,4}\s*/\s*[a-zđ]{1,4}\s*\)|^lưu\s+vt\b", re.IGNORECASE)
# Vietnamese person name: 2–6 capitalized words, no sentence punctuation.
_PERSON_NAME = re.compile(r"^[A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){1,5}\.?$")
# Studocu watermark stamped on scanned PDFs ("lOMoARcPSD|40036395").
_WATERMARK = re.compile(r"^lOMoARcPSD\|?\d*\s*$", re.IGNORECASE)
# A TOC section swallows everything below it — entries come as dot leaders,
# bare page numbers or even Markdown tables, so line rules cannot catch them all.
_TOC_HEADING = re.compile(r"^m[ụu]c\s*l[ụu]c\s*:?\s*$", re.IGNORECASE)
_ANY_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+\S")

# Lines to skip right after a dropped "(đã ký)" marker: the signer's name.
_MAX_NAME_LINES_AFTER_SIGN = 2


def clean_text(text: str) -> str:
    """Normalize text before chunking without altering Markdown structure."""
    text = _CONTROL_LINE_BREAKS.sub(" ", text)
    kept_lines = _drop_noise_lines(text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept_lines)).strip()


def _drop_noise_lines(lines: list[str]) -> list[str]:
    """Drop layout-noise lines, leaving tables and fenced code untouched."""
    kept: list[str] = []
    in_fence = False
    in_table = False
    names_to_skip = 0
    in_distribution_list = False
    in_toc_section = False

    for line in lines:
        stripped = line.strip()

        if _FENCE.match(stripped):
            in_fence = not in_fence
            kept.append(line)
            continue
        if in_fence:
            kept.append(line)
            continue
        if in_toc_section:
            # The whole "MỤC LỤC" section is noise, tables included; it ends at
            # a heading or at the first line that no longer reads like a TOC
            # entry (real content often follows without an intervening heading).
            if _ANY_HEADING.match(stripped) and not _TOC_HEADING.match(_ATX_PREFIX.sub("", stripped)):
                in_toc_section = False
                kept.append(line)
                continue
            if stripped.startswith("|") or _HTML_TABLE_START.search(stripped):
                continue
            title = _ATX_PREFIX.sub("", stripped)
            plain = title.strip("*_ ").strip()
            if plain and not _TOC_LINE_LIKE.search(plain):
                in_toc_section = False
                # Fall through to the normal rules for this line.
            else:
                continue
        if _TOC_HEADING.match(_ATX_PREFIX.sub("", stripped)):
            in_toc_section = True
            continue
        if in_table:
            in_table = not _HTML_TABLE_END.search(stripped)
            kept.append(line)
            continue
        if _HTML_TABLE_START.search(stripped):
            in_table = not _HTML_TABLE_END.search(stripped)
            kept.append(line)
            continue
        if stripped.startswith("|"):
            kept.append(line)
            continue
        if not stripped:
            # Blank lines do not end a "Nơi nhận" list: its items follow one.
            kept.append(line)
            continue

        title = _ATX_PREFIX.sub("", stripped)
        plain = title.strip("*_ ").strip()

        if names_to_skip > 0:
            if _PERSON_NAME.match(plain):
                names_to_skip -= 1
                continue
            names_to_skip = 0

        if in_distribution_list:
            if _is_distribution_item(stripped):
                continue
            in_distribution_list = False

        if _is_noise_line(title, plain):
            if _SIGNED_MARK.match(plain):
                names_to_skip = _MAX_NAME_LINES_AFTER_SIGN
            elif _NOI_NHAN.match(plain):
                in_distribution_list = True
            continue

        kept.append(line)

    return kept


def is_noise_line(line: str) -> bool:
    """Return True when a raw Markdown line (heading or plain) is layout noise."""
    stripped = line.strip()
    title = _ATX_PREFIX.sub("", stripped)
    plain = title.strip("*_ ").strip()
    return _is_noise_line(title, plain)


def _is_toc_entry(title: str) -> bool:
    """A single trailing dot-leader run marks a TOC entry or a blank form field.

    Form templates mix several runs in one line ("Họ và tên: ….. Nam (Nữ): …..")
    and must survive; a lone trailing run carries no answer content.
    """
    if not _TOC_DOT_LEADER.search(title):
        return False
    return len(_LEADER_RUN.findall(title)) == 1


def _is_noise_line(title: str, plain: str) -> bool:
    if _is_toc_entry(title) or _BOLD_PAGE_SUFFIX.search(title):
        return True
    if _PAGE_NUMBER_ONLY.match(plain):
        return True
    if _NATIONAL_TITLE.match(plain) or _NATIONAL_MOTTO.match(plain):
        return True
    if _PLACE_DATELINE.match(plain):
        return True
    if _SIGNER_ROLE.match(plain) or _SIGNED_MARK.match(plain):
        return True
    if _WATERMARK.match(plain):
        return True
    if _NOI_NHAN.match(plain):
        return True
    return False


def _is_distribution_item(line: str) -> bool:
    """Distribution entries after "Nơi nhận": bullets like "- Ban GĐHV (b/c);"."""
    stripped = line.strip().lstrip("-*+ ").strip()
    if not stripped:
        return True
    return bool(_DISTRIBUTION_MARKER.search(stripped))

from dataclasses import dataclass
import re

from app.ingestion.cleaner import clean_text

_HR_ONLY = re.compile(r"^(\*\s*){3,}$|^(-\s*){3,}$|^(_\s*){3,}$")
_HTML_TABLE_START = re.compile(r"<table\b", re.IGNORECASE)
_HTML_TABLE_END = re.compile(r"</table\s*>", re.IGNORECASE)
_HTML_THEAD = re.compile(r"<thead\b[^>]*>.*?</thead\s*>", re.IGNORECASE | re.DOTALL)
_HTML_TR = re.compile(r"<tr\b[^>]*>.*?</tr\s*>", re.IGNORECASE | re.DOTALL)
_HTML_TBODY = re.compile(r"<tbody\b[^>]*>.*?</tbody\s*>", re.IGNORECASE | re.DOTALL)

# Sentence units end at ".", ";", "!", "?" followed by whitespace, or at a newline.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+")
_PARAGRAPH_SPLIT = re.compile(r"\n{2,}")

# Children/parents shorter than this merge into their neighbour inside the same
# section whenever the size budget allows (RAG-06 default, configurable).
DEFAULT_MIN_CHILD_CHARS = 120


@dataclass(frozen=True)
class Chunk:
    text: str
    index: int
    heading: str = ""
    heading_level: int | None = None
    section_path: str = ""


@dataclass(frozen=True)
class Section:
    text: str
    heading: str = ""
    heading_level: int | None = None
    section_path: str = ""


@dataclass(frozen=True)
class ParentChildChunk:
    """A small searchable child paired with its larger generation parent."""

    text: str
    index: int
    parent_text: str
    parent_index: int
    child_index: int
    heading: str = ""
    heading_level: int | None = None
    section_path: str = ""


def compose_search_text(document_title: str, section_path: str, text: str) -> str:
    """Build the searchable text: context header (title > section path) + body.

    Embedding and BM25 run on this field so every chunk carries its document and
    section context (e.g. "BHYT" for an insurance clause that never spells it out);
    the plain ``text`` stays what users see and what feeds the prompt.
    """
    header = " > ".join(part for part in (document_title.strip(), section_path.strip()) if part)
    if not header:
        return text
    return f"{header}\n{text}"


def split_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    min_chunk_len: int = 0,
) -> list[Chunk]:
    """Split raw text into sized chunks while preserving markdown section structure."""
    cleaned = clean_text(text)
    if not cleaned:
        return []

    chunks: list[Chunk] = []
    for section in _split_markdown_sections(cleaned):
        chunks.extend(
            _split_section(
                section,
                chunk_size,
                chunk_overlap,
                start_index=len(chunks),
                min_chunk_len=min_chunk_len,
            )
        )

    return chunks


def split_parent_child(
    text: str,
    parent_size: int,
    parent_overlap: int,
    child_size: int,
    child_overlap: int,
    min_child_size: int | None = None,
) -> list[ParentChildChunk]:
    """Create searchable child chunks while retaining larger parent context.

    Parents never cross a heading boundary: one parent = one Điều/mục section, and
    an oversized section becomes several parents, each grouping consecutive
    Khoản/paragraphs (RAG-06). Children split within their parent at clause/
    paragraph boundaries; undersized pieces merge into their neighbour.
    """
    min_child = DEFAULT_MIN_CHILD_CHARS if min_child_size is None else min_child_size
    min_child = max(0, min(min_child, child_size))

    cleaned = clean_text(text)
    if not cleaned:
        return []

    output: list[ParentChildChunk] = []
    parent_counter = 0
    for section in _split_markdown_sections(cleaned):
        heading_line, body = _separate_heading(section)
        if not body:
            continue

        heading_context = f"{heading_line}\n\n" if heading_line else ""
        parent_budget = parent_size - len(heading_context)
        if parent_budget <= 0:
            heading_context = ""
            parent_budget = parent_size

        parent_min = min(min_child, parent_budget)
        parent_bodies = _split_body_pieces(body, parent_budget, parent_overlap, min_len=parent_min)
        for parent_body in parent_bodies:
            parent_text = f"{heading_context}{parent_body}".strip()
            child_budget = child_size - len(heading_context)
            child_context = heading_context if child_budget > 0 else ""
            if child_budget <= 0:
                child_budget = child_size

            child_bodies = _split_body_pieces(parent_body, child_budget, child_overlap, min_len=min_child)
            if not child_bodies:
                child_bodies = [parent_body]

            for child_index, child_body in enumerate(child_bodies):
                output.append(
                    ParentChildChunk(
                        text=f"{child_context}{child_body}".strip(),
                        index=len(output),
                        parent_text=parent_text,
                        parent_index=parent_counter,
                        child_index=child_index,
                        heading=section.heading,
                        heading_level=section.heading_level,
                        section_path=section.section_path,
                    )
                )
            parent_counter += 1

    return output


def _split_markdown_sections(text: str) -> list[Section]:
    """Split markdown text into sections at heading boundaries and track heading hierarchy."""
    sections: list[Section] = []
    current_lines: list[str] = []
    current_heading = ""
    current_level: int | None = None
    current_path = ""
    heading_stack: list[tuple[int, str]] = []

    for line in text.splitlines():
        heading = _parse_heading(line)
        if heading:
            if current_lines:
                sections.append(
                    Section(
                        text="\n".join(current_lines).strip(),
                        heading=current_heading,
                        heading_level=current_level,
                        section_path=current_path,
                    )
                )

            level, title = heading
            heading_stack = [(item_level, item_title) for item_level, item_title in heading_stack if item_level < level]
            heading_stack.append((level, title))
            current_heading = title
            current_level = level
            current_path = " > ".join(item_title for _, item_title in heading_stack)
            current_lines = [line]
            continue

        current_lines.append(line)

    if current_lines:
        sections.append(
            Section(
                text="\n".join(current_lines).strip(),
                heading=current_heading,
                heading_level=current_level,
                section_path=current_path,
            )
        )

    return [section for section in sections if section.text]


def _split_body_pieces(
    body: str,
    chunk_size: int,
    chunk_overlap: int,
    min_len: int = 0,
) -> list[str]:
    """Split a heading-less body into size-bounded pieces at block boundaries."""
    if not body.strip():
        return []

    blocks = _split_blocks(body)
    if not blocks:
        return []

    compact = "\n\n".join(blocks)
    if len(compact) <= chunk_size:
        return [compact]

    pieces: list[str] = []
    current = ""
    intro_threshold = min(200, max(1, chunk_size // 3))

    for block in blocks:
        if _is_markdown_table(block) or _is_html_table(block):
            table_budget = chunk_size
            prefix = ""
            if current and not _is_markdown_table(current) and not _is_html_table(current):
                if len(current) <= intro_threshold:
                    prefix = current
                    table_budget = chunk_size - len(prefix) - (2 if prefix else 0)
                    current = ""
                else:
                    pieces.append(current)
                    current = ""

            if table_budget <= 0:
                table_budget = chunk_size
                if prefix:
                    pieces.append(prefix)
                    prefix = ""

            if len(block) > table_budget:
                table_pieces = _split_oversized_table_block(block, table_budget, chunk_overlap)
                if prefix and table_pieces:
                    table_pieces[0] = f"{prefix}\n\n{table_pieces[0]}".strip()
                elif prefix:
                    pieces.append(prefix)
                pieces.extend(table_pieces)
            else:
                merged = f"{prefix}\n\n{block}".strip() if prefix else block
                if len(merged) <= chunk_size:
                    pieces.append(merged)
                else:
                    if prefix:
                        pieces.append(prefix)
                    pieces.append(block)
            continue

        if len(block) > chunk_size:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_split_long_block(block, chunk_size, chunk_overlap))
            continue

        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            pieces.append(current)
        current = block

    if current:
        pieces.append(current)

    pieces = [piece for piece in pieces if piece.strip()]
    if min_len > 0:
        pieces = _merge_short_pieces(pieces, chunk_size, min_len)
    return pieces


def _merge_short_pieces(pieces: list[str], limit: int, min_len: int) -> list[str]:
    """Fold pieces shorter than ``min_len`` into their neighbour, same section.

    A trailing fragment first tries to join the previous piece outright; when the
    two do not fit together, trailing blocks/sentences migrate backwards until the
    tail reaches ``min_len``. Pieces therefore stay within ``limit`` and a piece
    ends up under ``min_len`` only when the whole body was that short.
    """
    if min_len <= 0 or len(pieces) <= 1:
        return pieces

    merged = [pieces[0]]
    for piece in pieces[1:]:
        prev = merged[-1]
        if len(prev) >= min_len:
            merged.append(piece)
        elif len(prev) + 2 + len(piece) <= limit:
            merged[-1] = f"{prev}\n\n{piece}"
        elif _is_markdown_table(piece) or _is_html_table(piece):
            # Tables legitimately exceed the soft budget; their leading note
            # (e.g. "Chi tiết xem tại …") folds into the first table piece.
            merged[-1] = f"{prev}\n\n{piece}"
        else:
            moved = _steal_leading_units(prev, piece, limit, min_len)
            if moved is None:
                merged.append(piece)
            else:
                merged[-1], piece = moved
                merged.append(piece)

    guard = 0
    while len(merged) >= 2 and len(merged[-1]) < min_len and guard < 100:
        guard += 1
        prev, last = merged[-2], merged[-1]
        if len(prev) + 2 + len(last) <= limit:
            merged[-2:] = [f"{prev}\n\n{last}"]
            break
        if (_is_markdown_table(prev) or _is_html_table(prev)) and not (
            _is_markdown_table(last) or _is_html_table(last)
        ):
            # Keep a short trailing note attached to its table instead of
            # emitting a near-empty chunk.
            merged[-2:] = [f"{prev}\n\n{last}"]
            break
        moved = _steal_trailing_unit(prev, last, limit, min_len)
        if moved is None:
            break
        merged[-2:] = [moved[0], moved[1]]

    return [piece for piece in merged if piece.strip()]


def _steal_trailing_unit(prev: str, last: str, limit: int, min_len: int) -> tuple[str, str] | None:
    """Move the last block/sentence of ``prev`` to the front of ``last``.

    Refuses to shrink ``prev`` below ``min_len`` — rebalancing must not push the
    shortness problem onto the previous piece.
    """
    units, separator = _split_units(prev)
    if len(units) < 2:
        return None

    unit = units.pop()
    new_prev = separator.join(units).strip()
    new_last = f"{unit}{separator}{last}".strip()
    if not new_prev or len(new_prev) < min_len or len(new_last) > limit:
        return None
    return new_prev, new_last


def _steal_leading_units(prev: str, piece: str, limit: int, min_len: int) -> tuple[str, str] | None:
    """Move leading blocks/sentences of ``piece`` back into ``prev`` until it reaches ``min_len``."""
    if _is_markdown_table(piece) or _is_html_table(piece):
        return None
    units, separator = _split_units(piece)
    if len(units) < 2:
        return None

    new_prev = prev
    while len(new_prev) < min_len and units:
        candidate = f"{new_prev}{separator}{units[0]}".strip()
        if len(candidate) > limit:
            break
        new_prev = candidate
        units.pop(0)

    if not units or len(new_prev) == len(prev):
        return None
    return new_prev, separator.join(units).strip()


def _split_units(text: str) -> tuple[list[str], str]:
    """Split a piece into movable units: paragraphs (\\n\\n) or sentences (space)."""
    blocks = [block for block in _PARAGRAPH_SPLIT.split(text) if block.strip()]
    if len(blocks) > 1 and not any(_is_markdown_table(block) or _is_html_table(block) for block in blocks):
        return blocks, "\n\n"

    if not (_is_markdown_table(text) or _is_html_table(text)):
        sentences = _split_sentences(text)
        if len(sentences) > 1:
            return sentences, " "
    return [text], "\n\n"


def _split_sentences(text: str) -> list[str]:
    """Split text at sentence boundaries (., ;, !, ?, newline), keeping terminators."""
    return [unit.strip() for unit in _SENTENCE_SPLIT.split(text) if unit.strip()]


def _split_section(
    section: Section,
    chunk_size: int,
    chunk_overlap: int,
    start_index: int,
    min_chunk_len: int = 0,
) -> list[Chunk]:
    """Split one section into chunks that respect paragraph boundaries and size limits."""
    heading_line, body = _separate_heading(section)
    if not body:
        return []

    heading_context = f"{heading_line}\n\n" if heading_line else ""
    body_chunk_size = chunk_size - len(heading_context)
    if body_chunk_size <= 0:
        heading_context = ""
        body_chunk_size = chunk_size

    pieces = _split_body_pieces(body, body_chunk_size, chunk_overlap, min_len=min_chunk_len)
    return [
        _build_chunk(f"{heading_context}{piece}".strip(), section, start_index + offset)
        for offset, piece in enumerate(pieces)
        if piece.strip()
    ]


def _separate_heading(section: Section) -> tuple[str, str]:
    """Return the leading markdown heading and substantive section body separately."""
    lines = section.text.splitlines()
    if lines and _parse_heading(lines[0]):
        return lines[0].strip(), "\n".join(lines[1:]).strip()
    return "", section.text.strip()


def _split_blocks(text: str) -> list[str]:
    """Split paragraphs and keep each Markdown/HTML table as a distinct block."""
    lines = text.splitlines()
    blocks: list[str] = []
    current: list[str] = []
    index = 0

    def flush_current() -> None:
        block = "\n".join(current).strip()
        if block and not _is_horizontal_rule(block):
            blocks.append(block)
        current.clear()

    while index < len(lines):
        html_table = _extract_html_table(lines, index)
        if html_table is not None:
            flush_current()
            table_text, next_index = html_table
            blocks.append(table_text)
            index = next_index
            continue

        if _starts_markdown_table(lines, index):
            flush_current()
            table_lines = [lines[index].strip(), lines[index + 1].strip()]
            index += 2
            while index < len(lines):
                line = lines[index]
                if _parse_heading(line) or _HTML_TABLE_START.search(line):
                    break

                stripped = line.strip()
                last = table_lines[-1]
                last_incomplete = last.startswith("|") and not last.endswith("|")

                if last_incomplete:
                    # Absorb blank lines and text until the open row closes with "|".
                    if stripped:
                        table_lines[-1] = f"{last} {stripped}"
                    index += 1
                    continue

                if _looks_like_table_row(line):
                    table_lines.append(stripped)
                    index += 1
                    continue

                if stripped.startswith("|") and not stripped.endswith("|"):
                    table_lines.append(stripped)
                    index += 1
                    continue

                if not stripped:
                    break

                # Soft wrap inside an otherwise closed row.
                table_lines[-1] = f"{last} {stripped}"
                index += 1
            blocks.append("\n".join(table_lines))
            continue

        if not lines[index].strip():
            flush_current()
        else:
            current.append(lines[index])
        index += 1

    flush_current()
    return blocks


def _is_horizontal_rule(text: str) -> bool:
    return bool(_HR_ONLY.match(text.strip()))


def _extract_html_table(lines: list[str], index: int) -> tuple[str, int] | None:
    """Return an HTML table block starting at index, or None."""
    line = lines[index]
    if not _HTML_TABLE_START.search(line):
        return None

    collected = [line]
    if _HTML_TABLE_END.search(line):
        return "\n".join(collected).strip(), index + 1

    next_index = index + 1
    while next_index < len(lines):
        collected.append(lines[next_index])
        if _HTML_TABLE_END.search(lines[next_index]):
            return "\n".join(collected).strip(), next_index + 1
        next_index += 1

    return "\n".join(collected).strip(), next_index


def _starts_markdown_table(lines: list[str], index: int) -> bool:
    """Return whether two lines form a Markdown table header and delimiter."""
    if index + 1 >= len(lines) or not _looks_like_table_row(lines[index]):
        return False
    cells = _table_cells_safe(lines[index + 1])
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def _looks_like_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _table_cells(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return stripped.split("|") if stripped else []


def _table_cells_safe(line: str) -> list[str]:
    """Split a table row into cells while ignoring escaped and fenced pipes."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|"):
        stripped = stripped[:-1]

    cells: list[str] = []
    current: list[str] = []
    in_backticks = False
    in_math = False
    index = 0
    while index < len(stripped):
        char = stripped[index]
        if char == "\\" and index + 1 < len(stripped):
            current.append(stripped[index : index + 2])
            index += 2
            continue
        if char == "`":
            in_backticks = not in_backticks
            current.append(char)
            index += 1
            continue
        if char == "$" and not in_backticks:
            in_math = not in_math
            current.append(char)
            index += 1
            continue
        if char == "|" and not in_backticks and not in_math:
            cells.append("".join(current))
            current = []
            index += 1
            continue
        current.append(char)
        index += 1

    cells.append("".join(current))
    return cells


def _is_markdown_table(text: str) -> bool:
    return _starts_markdown_table(text.splitlines(), 0)


def _is_html_table(text: str) -> bool:
    return bool(_HTML_TABLE_START.match(text.lstrip()))


def _split_oversized_table_block(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if _is_markdown_table(text):
        return _split_long_table(text, chunk_size)
    if _is_html_table(text):
        return _split_long_html_table(text, chunk_size)
    return _split_long_block(text, chunk_size, chunk_overlap)


def _table_split_limits(chunk_size: int) -> tuple[int, int]:
    """Return (soft_limit, hard_limit) for packing table rows.

    Repeated headers are useful context but should not force one-row chunks when
    child_size is only modestly larger than the header itself.
    """
    soft = max(1, chunk_size)
    hard = max(soft * 2, soft + 200)
    return soft, hard


def _should_flush_table_rows(
    current_rows: list[str],
    candidate_len: int,
    soft_limit: int,
    hard_limit: int,
    *,
    min_rows: int = 3,
) -> bool:
    """Flush when over budget, but keep packing until min_rows unless hard-capped."""
    if not current_rows:
        return False
    if candidate_len <= soft_limit:
        return False
    if len(current_rows) >= min_rows:
        return True
    return candidate_len > hard_limit


def _split_long_table(text: str, chunk_size: int) -> list[str]:
    """Split a table between rows and repeat its header in every resulting piece."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return [text]

    header = lines[:2]
    rows = lines[2:]
    header_text = "\n".join(header)
    if not rows:
        return [header_text]

    soft_limit, hard_limit = _table_split_limits(chunk_size)
    pieces: list[str] = []
    current_rows: list[str] = []
    for row in rows:
        candidate = "\n".join([*header, *current_rows, row])
        if _should_flush_table_rows(current_rows, len(candidate), soft_limit, hard_limit):
            pieces.append("\n".join([*header, *current_rows]))
            current_rows = [row]
        else:
            current_rows.append(row)

    if current_rows:
        pieces.append("\n".join([*header, *current_rows]))
    return _merge_short_table_tail(pieces, header, hard_limit)


def _merge_short_table_tail(
    pieces: list[str],
    header: list[str],
    hard_limit: int,
    *,
    min_rows: int = 3,
) -> list[str]:
    """Fold a trailing undersized table fragment into the previous piece when possible."""
    if len(pieces) < 2:
        return pieces

    header_len = len(header)
    def data_rows(piece: str) -> list[str]:
        lines = [line for line in piece.splitlines() if line.strip()]
        return lines[header_len:]

    last_rows = data_rows(pieces[-1])
    if len(last_rows) >= min_rows:
        return pieces

    prev_rows = data_rows(pieces[-2])
    merged = "\n".join([*header, *prev_rows, *last_rows])
    if len(merged) > hard_limit:
        return pieces

    return [*pieces[:-2], merged]


def _split_long_html_table(text: str, chunk_size: int) -> list[str]:
    """Split an HTML table between body rows and repeat thead in every piece."""
    thead_match = _HTML_THEAD.search(text)
    thead = thead_match.group(0) if thead_match else ""

    tbody_match = _HTML_TBODY.search(text)
    body_region = tbody_match.group(0) if tbody_match else text
    rows = _HTML_TR.findall(body_region)
    if thead:
        # Prefer body rows; if thead rows were included, drop duplicates that match thead trs.
        thead_rows = set(_HTML_TR.findall(thead))
        rows = [row for row in rows if row not in thead_rows]

    if not rows:
        return [text]

    open_tag_match = re.search(r"<table\b[^>]*>", text, flags=re.IGNORECASE)
    open_tag = open_tag_match.group(0) if open_tag_match else "<table>"
    close_tag = "</table>"

    def render(body_rows: list[str]) -> str:
        parts = [open_tag]
        if thead:
            parts.append(thead)
        parts.append("<tbody>")
        parts.extend(body_rows)
        parts.append("</tbody>")
        parts.append(close_tag)
        return "\n".join(parts)

    soft_limit, hard_limit = _table_split_limits(chunk_size)
    pieces: list[str] = []
    current_rows: list[str] = []
    for row in rows:
        candidate_rows = [*current_rows, row]
        if _should_flush_table_rows(
            current_rows,
            len(render(candidate_rows)),
            soft_limit,
            hard_limit,
        ):
            pieces.append(render(current_rows))
            current_rows = [row]
        else:
            current_rows.append(row)

    if current_rows:
        pieces.append(render(current_rows))
    if not pieces:
        return [text]
    if len(pieces) < 2:
        return pieces

    # Merge a short trailing fragment when under the hard cap.
    last_rows = _HTML_TR.findall(pieces[-1])
    if thead:
        thead_rows = set(_HTML_TR.findall(thead))
        last_rows = [row for row in last_rows if row not in thead_rows]
    if 0 < len(last_rows) < 3:
        prev_rows = _HTML_TR.findall(pieces[-2])
        if thead:
            prev_rows = [row for row in prev_rows if row not in thead_rows]
        merged = render([*prev_rows, *last_rows])
        if len(merged) <= hard_limit:
            return [*pieces[:-2], merged]
    return pieces


def _split_long_block(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split an oversized prose block at sentence boundaries, never mid-word."""
    units = _split_sentences(text)
    if not units:
        return []

    pieces = _pack_units(units, chunk_size)
    return _apply_sentence_overlap(pieces, chunk_size, chunk_overlap)


def _pack_units(units: list[str], limit: int) -> list[str]:
    """Greedily pack sentence units into pieces of at most ``limit`` characters."""
    pieces: list[str] = []
    current = ""
    for unit in units:
        if len(unit) > limit:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_split_oversized_unit(unit, limit))
            continue

        candidate = f"{current} {unit}" if current else unit
        if len(candidate) <= limit:
            current = candidate
        else:
            pieces.append(current)
            current = unit

    if current:
        pieces.append(current)
    return pieces


def _split_oversized_unit(unit: str, limit: int) -> list[str]:
    """Cut an unbreakable unit at whitespace so no piece starts mid-word."""
    pieces: list[str] = []
    rest = unit
    while len(rest) > limit:
        cut = rest.rfind(" ", 1, limit + 1)
        if cut <= 0:
            cut = limit
        piece = rest[:cut].strip()
        if piece:
            pieces.append(piece)
        rest = rest[cut:].lstrip()

    rest = rest.strip()
    if rest:
        pieces.append(rest)
    return pieces


def _apply_sentence_overlap(pieces: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    """Prepend a word-aligned tail of the previous piece when overlap is enabled."""
    if chunk_overlap <= 0 or len(pieces) < 2:
        return pieces

    output = [pieces[0]]
    for piece in pieces[1:]:
        tail = _tail_at_word_boundary(output[-1], chunk_overlap)
        if not tail:
            output.append(piece)
            continue
        candidate = f"{tail} {piece}"
        output.append(candidate if len(candidate) <= chunk_size else piece)
    return output


def _tail_at_word_boundary(text: str, overlap: int) -> str:
    """Return up to ``overlap`` trailing characters, starting at a word boundary."""
    if overlap <= 0 or len(text) <= overlap:
        return ""
    start = len(text) - overlap
    if not text[start - 1].isspace():
        space = text.find(" ", start)
        if space == -1:
            return ""
        start = space + 1
    return text[start:]


def _build_chunk(text: str, section: Section, index: int) -> Chunk:
    """Create a Chunk with text content and inherited section metadata."""
    return Chunk(
        text=text,
        index=index,
        heading=section.heading,
        heading_level=section.heading_level,
        section_path=section.section_path,
    )


def _parse_heading(line: str) -> tuple[int, str] | None:
    """Parse a markdown heading line and return its level and title, or None if not a heading."""
    match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", line)
    if not match:
        return None

    title = _normalize_heading(match.group(2))
    if not title:
        return None

    return len(match.group(1)), title


def _normalize_heading(value: str) -> str:
    """Strip inline markdown and HTML from a heading title for consistent metadata."""
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[*_`]+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" #")

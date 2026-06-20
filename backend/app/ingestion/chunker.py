from dataclasses import dataclass
import re

from app.ingestion.cleaner import clean_text


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


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    """Split raw text into sized chunks while preserving markdown section structure."""
    cleaned = clean_text(text)
    if not cleaned:
        return []

    chunks: list[Chunk] = []
    for section in _split_markdown_sections(cleaned):
        chunks.extend(_split_section(section, chunk_size, chunk_overlap, start_index=len(chunks)))

    return chunks


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


def _split_section(
    section: Section,
    chunk_size: int,
    chunk_overlap: int,
    start_index: int,
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

    if len(body) <= body_chunk_size:
        return [_build_chunk(f"{heading_context}{body}".strip(), section, start_index)]

    pieces: list[str] = []
    current = ""

    for block in _split_blocks(body):
        if len(block) > body_chunk_size:
            if current:
                pieces.append(current)
                current = ""
            if _is_markdown_table(block):
                pieces.extend(_split_long_table(block, body_chunk_size))
            else:
                pieces.extend(_split_long_block(block, body_chunk_size, chunk_overlap))
            continue

        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= body_chunk_size:
            current = candidate
            continue

        if current:
            pieces.append(current)
        current = block

    if current:
        pieces.append(current)

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
    """Split paragraphs and keep each Markdown table as a distinct block."""
    lines = text.splitlines()
    blocks: list[str] = []
    current: list[str] = []
    index = 0

    def flush_current() -> None:
        block = "\n".join(current).strip()
        if block:
            blocks.append(block)
        current.clear()

    while index < len(lines):
        if _starts_markdown_table(lines, index):
            flush_current()
            table_lines = [lines[index].strip(), lines[index + 1].strip()]
            index += 2
            while index < len(lines) and _looks_like_table_row(lines[index]):
                table_lines.append(lines[index].strip())
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


def _starts_markdown_table(lines: list[str], index: int) -> bool:
    """Return whether two lines form a Markdown table header and delimiter."""
    if index + 1 >= len(lines) or not _looks_like_table_row(lines[index]):
        return False
    cells = _table_cells(lines[index + 1])
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def _looks_like_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _table_cells(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return stripped.split("|") if stripped else []


def _is_markdown_table(text: str) -> bool:
    return _starts_markdown_table(text.splitlines(), 0)


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

    pieces: list[str] = []
    current_rows: list[str] = []
    for row in rows:
        candidate = "\n".join([*header, *current_rows, row])
        if current_rows and len(candidate) > chunk_size:
            pieces.append("\n".join([*header, *current_rows]))
            current_rows = [row]
        else:
            current_rows.append(row)

    if current_rows:
        pieces.append("\n".join([*header, *current_rows]))
    return pieces


def _split_long_block(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split an oversized block into fixed-size pieces with sliding overlap."""
    pieces: list[str] = []
    step = max(1, chunk_size - max(0, chunk_overlap))
    start = 0

    while start < len(text):
        end = min(len(text), start + chunk_size)
        pieces.append(text[start:end].strip())
        if end == len(text):
            break
        start += step

    return [piece for piece in pieces if piece]


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

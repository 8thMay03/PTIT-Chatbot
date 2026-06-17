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
    cleaned = clean_text(text)
    if not cleaned:
        return []

    chunks: list[Chunk] = []
    for section in _split_markdown_sections(cleaned):
        chunks.extend(_split_section(section, chunk_size, chunk_overlap, start_index=len(chunks)))

    return chunks


def _split_markdown_sections(text: str) -> list[Section]:
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
    if len(section.text) <= chunk_size:
        return [_build_chunk(section.text, section, start_index)]

    pieces: list[str] = []
    current = ""

    for block in _split_blocks(section.text):
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

    return [
        _build_chunk(_with_heading_context(piece, section), section, start_index + offset)
        for offset, piece in enumerate(pieces)
        if piece.strip()
    ]


def _split_blocks(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]


def _split_long_block(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
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


def _with_heading_context(text: str, section: Section) -> str:
    if not section.heading or _parse_heading(text.splitlines()[0] if text.splitlines() else ""):
        return text

    level = section.heading_level or 2
    heading_line = f"{'#' * level} {section.heading}"
    return f"{heading_line}\n\n{text}".strip()


def _build_chunk(text: str, section: Section, index: int) -> Chunk:
    return Chunk(
        text=text,
        index=index,
        heading=section.heading,
        heading_level=section.heading_level,
        section_path=section.section_path,
    )


def _parse_heading(line: str) -> tuple[int, str] | None:
    match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", line)
    if not match:
        return None

    title = _normalize_heading(match.group(2))
    if not title:
        return None

    return len(match.group(1)), title


def _normalize_heading(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[*_`]+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" #")

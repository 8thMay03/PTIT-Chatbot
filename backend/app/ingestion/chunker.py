from dataclasses import dataclass
import re

from app.ingestion.cleaner import clean_text


@dataclass(frozen=True)
class Chunk:
    text: str
    index: int


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    cleaned = clean_text(text)
    if not cleaned:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= chunk_size:
            current = f"{current}\n\n{paragraph}".strip()
            continue

        if current:
            chunks.append(current)
        current = paragraph

        while len(current) > chunk_size:
            chunks.append(current[:chunk_size])
            start = max(0, chunk_size - chunk_overlap)
            current = current[start:]

    if current:
        chunks.append(current)

    return [Chunk(text=value, index=index) for index, value in enumerate(chunks)]

"""Read UTF-8 Markdown and plain text without conversion."""

from pathlib import Path

TEXT_EXTENSIONS = frozenset({".md", ".txt"})


class TextParser:
    name = "text"
    extensions = TEXT_EXTENSIONS

    def parse(self, path: Path, *, convert: bool = True) -> str:
        return path.read_text(encoding="utf-8")

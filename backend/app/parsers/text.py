"""Read UTF-8 Markdown and plain text without conversion."""

from pathlib import Path

from app.parsers.base import ProgressCallback

TEXT_EXTENSIONS = frozenset({".md", ".txt"})


class TextParser:
    name = "text"
    extensions = TEXT_EXTENSIONS

    def parse(
        self,
        path: Path,
        *,
        convert: bool = True,
        on_progress: ProgressCallback | None = None,
    ) -> str:
        if on_progress is not None:
            on_progress(60, "Đang đọc văn bản")
        text = path.read_text(encoding="utf-8")
        if on_progress is not None:
            on_progress(85, "Đã đọc văn bản")
        return text

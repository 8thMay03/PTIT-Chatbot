import re

# Form feed / vertical tab split lines via str.splitlines() and break Markdown tables.
_CONTROL_LINE_BREAKS = re.compile(r"[\f\v]+")


def clean_text(text: str) -> str:
    """Normalize text before chunking without altering Markdown structure."""
    text = _CONTROL_LINE_BREAKS.sub(" ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

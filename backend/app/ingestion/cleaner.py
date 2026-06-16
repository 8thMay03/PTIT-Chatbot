import re


def clean_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()

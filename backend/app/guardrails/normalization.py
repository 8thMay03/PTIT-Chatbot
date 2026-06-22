import re
import unicodedata


def normalize_text(value: str) -> str:
    """Normalize user text for deterministic domain and task matching."""

    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def security_normalize(value: str) -> str:
    """Normalize common Unicode, spacing and leetspeak obfuscation."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", normalized)
    normalized = normalized.translate(
        str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"})
    )
    normalized = re.sub(r"[^\w+#<>\[\]]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())

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
    # Giữ ":" để nhận diện tiêu đề vai trò giả như "### system:".
    normalized = re.sub(r"[^\w+#<>\[\]:]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def strip_accents(value: str) -> str:
    """Remove Vietnamese diacritics (NFC or NFD input), mapping đ/Đ to d/D."""

    decomposed = unicodedata.normalize("NFD", value)
    stripped = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return unicodedata.normalize("NFC", stripped.replace("đ", "d").replace("Đ", "D"))


def has_accents(value: str) -> bool:
    """Return whether the text carries any diacritic that strip_accents would remove."""

    return strip_accents(value) != value

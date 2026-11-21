"""Sinh biến thể lỗi gõ của câu hỏi tiếng Việt để đo bước sửa câu (task llm-query-correction).

Hàm thuần, chỉ dùng ``random.Random`` truyền vào nên cùng seed cho cùng kết quả. Các loại lỗi:

- ``strip_all``: bỏ hết dấu.
- ``strip_partial``: bỏ dấu khoảng một nửa số chữ có dấu (ít nhất một chữ).
- ``wrong_tone``: đổi dấu thanh của một chữ (``phí`` → ``phì``), chữ không dấu thanh thì thêm.
- ``telex_leftover``: một chữ gõ Telex khi bộ gõ tắt (``học`` → ``hocj``, ``nhiêu`` → ``nhieeu``).
- ``char_noise``: thêm, bớt hoặc đổi chỗ một ký tự trong một chữ.
- ``merge_words``: dính hai chữ liền nhau (``học phí`` → ``họcphí``).
- ``drop_punct``: bỏ dấu câu.

Bộ lỗi gõ (:func:`make_typo_variant`): mỗi câu 1–3 loại lỗi khác nhau (trừ ``strip_all``),
chọn trong các loại áp dụng được, ghi lại loại đã áp dụng. Chữ có chữ số hoặc viết hoa toàn bộ
(``INT1340``, ``QLDT``) không bị gây lỗi: bộ sửa câu bắt giữ nguyên văn các chữ này.
"""

from __future__ import annotations

import random
import re
import unicodedata

from app.guardrails.normalization import strip_accents

PERTURB_MODES = ("none", "strip_all", "typo")
TYPO_TYPES = ("wrong_tone", "telex_leftover", "strip_partial", "char_noise", "merge_words", "drop_punct")

# Dấu thanh dạng tổ hợp (NFD) và phím Telex tương ứng.
TONE_MARKS = {
    "́": "s",  # sắc
    "̀": "f",  # huyền
    "̉": "r",  # hỏi
    "̃": "x",  # ngã
    "̣": "j",  # nặng
}
# Dấu mũ/móc/trăng trong NFD: (chữ gốc, dấu) → phím Telex.
VOWEL_MARK_TELEX = {
    ("a", "̂"): "aa",
    ("e", "̂"): "ee",
    ("o", "̂"): "oo",
    ("a", "̆"): "aw",
    ("o", "̛"): "ow",
    ("u", "̛"): "uw",
}
_WORD_RE = re.compile(r"\w+", re.UNICODE)
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_LETTERS = "abcdeghiklmnopqrstuvxy"


def _is_plain(word: str) -> bool:
    return (
        any(char.isalpha() for char in word)
        and not any(char.isdigit() for char in word)
        and not (len(word) >= 2 and word.isupper())
    )


def _words(text: str) -> list[re.Match]:
    """Chữ được phép gây lỗi: có chữ cái, không có chữ số, không viết hoa toàn bộ."""
    return [match for match in _WORD_RE.finditer(text) if _is_plain(match.group())]


def _replace_span(text: str, match: re.Match, replacement: str) -> str:
    return text[: match.start()] + replacement + text[match.end() :]


def _tone_of(word: str) -> str | None:
    for char in unicodedata.normalize("NFD", word):
        if char in TONE_MARKS:
            return char
    return None


def strip_all(text: str, rng: random.Random | None = None) -> str:
    return strip_accents(unicodedata.normalize("NFC", text))


def strip_partial(text: str, rng: random.Random) -> str | None:
    text = unicodedata.normalize("NFC", text)
    accented = [match for match in _words(text) if strip_accents(match.group()) != match.group()]
    if len(accented) < 2:
        return None  # một chữ có dấu thì bỏ dấu một phần cũng là bỏ hết
    chosen = rng.sample(accented, max(1, len(accented) // 2))
    for match in sorted(chosen, key=lambda item: item.start(), reverse=True):
        text = _replace_span(text, match, strip_accents(match.group()))
    return text


def wrong_tone(text: str, rng: random.Random) -> str | None:
    text = unicodedata.normalize("NFC", text)
    candidates = _words(text)
    if not candidates:
        return None
    match = rng.choice(candidates)
    word = unicodedata.normalize("NFD", match.group())
    current = _tone_of(word)
    choices = [mark for mark in TONE_MARKS if mark != current]
    new_mark = rng.choice(choices)
    if current is not None:
        # Đặt dấu mới cuối chuỗi dấu của nguyên âm rồi để NFC sắp lại theo combining class
        # (thay tại chỗ dấu nặng trước dấu mũ sẽ ra "ẻ̂" thay vì "ể").
        index = word.index(current)
        end = index
        while end < len(word) and unicodedata.category(word[end]) == "Mn":
            end += 1
        word = word[:index] + word[index + 1 : end] + new_mark + word[end:]
    else:
        # Không có dấu thanh: thêm vào nguyên âm có mũ/móc/trăng (ê, ơ, ă...), không có thì nguyên âm cuối.
        vowel_positions = [index for index, char in enumerate(word) if char.lower() in "aeiouy"]
        if not vowel_positions:
            return None
        marked = [
            index
            for index in vowel_positions
            if index + 1 < len(word) and unicodedata.category(word[index + 1]) == "Mn"
        ]
        position = (marked or vowel_positions)[-1] + 1
        while position < len(word) and unicodedata.category(word[position]) == "Mn":
            position += 1
        word = word[:position] + new_mark + word[position:]
    return _replace_span(text, match, unicodedata.normalize("NFC", word))


def to_telex(word: str) -> str:
    """Chữ có dấu → chuỗi phím Telex (dấu thanh gõ ở cuối chữ): ``học`` → ``hocj``."""

    decomposed = unicodedata.normalize("NFD", word)
    output: list[str] = []
    tone_key = ""
    for char in decomposed:
        if char in TONE_MARKS:
            tone_key = TONE_MARKS[char]
            continue
        if unicodedata.category(char) == "Mn":
            base = output[-1] if output else ""
            key = VOWEL_MARK_TELEX.get((base.lower(), char))
            if key is not None:
                output[-1] = key if base.islower() else key.capitalize()
            continue
        if char in "đĐ":
            output.append("dd" if char == "đ" else "Dd")
            continue
        output.append(char)
    return "".join(output) + tone_key


def telex_leftover(text: str, rng: random.Random) -> str | None:
    text = unicodedata.normalize("NFC", text)
    accented = [match for match in _words(text) if strip_accents(match.group()) != match.group()]
    if not accented:
        return None
    match = rng.choice(accented)
    return _replace_span(text, match, to_telex(match.group()))


def char_noise(text: str, rng: random.Random) -> str | None:
    text = unicodedata.normalize("NFC", text)
    candidates = [match for match in _words(text) if len(match.group()) >= 3]
    if not candidates:
        return None
    match = rng.choice(candidates)
    word = match.group()
    operation = rng.choice(("insert", "delete", "swap"))
    position = rng.randrange(1, len(word))
    if operation == "insert":
        word = word[:position] + rng.choice(_LETTERS) + word[position:]
    elif operation == "delete":
        word = word[:position] + word[position + 1 :]
    else:
        if word[position - 1] == word[position]:
            return None
        word = word[: position - 1] + word[position] + word[position - 1] + word[position + 1 :]
    return _replace_span(text, match, word)


def merge_words(text: str, rng: random.Random) -> str | None:
    words = list(_WORD_RE.finditer(text))
    # Khoảng trắng đơn giữa hai chữ thường liền nhau.
    gaps = [
        (left.end(), right.start())
        for left, right in zip(words, words[1:])
        if text[left.end() : right.start()] == " " and _is_plain(left.group()) and _is_plain(right.group())
    ]
    if not gaps:
        return None
    start, end = rng.choice(gaps)
    return text[:start] + text[end:]


def drop_punct(text: str, rng: random.Random | None = None) -> str | None:
    if not _PUNCT_RE.search(text):
        return None
    return " ".join(_PUNCT_RE.sub(" ", text).split())


TYPO_FUNCTIONS = {
    "wrong_tone": wrong_tone,
    "telex_leftover": telex_leftover,
    "strip_partial": strip_partial,
    "char_noise": char_noise,
    "merge_words": merge_words,
    "drop_punct": drop_punct,
}


def make_typo_variant(text: str, rng: random.Random, max_errors: int = 3) -> tuple[str, list[str]]:
    """Áp 1–``max_errors`` loại lỗi khác nhau, thứ tự ngẫu nhiên theo ``rng``.

    Trả ``(câu lỗi, các loại đã áp dụng)``. Loại không áp dụng được (câu không có dấu câu,
    chỉ một chữ có dấu...) bị bỏ và thay bằng loại khác.
    """

    wanted = rng.randint(1, max_errors)
    order = list(TYPO_TYPES)
    rng.shuffle(order)
    applied: list[str] = []
    current = unicodedata.normalize("NFC", text)
    for name in order:
        if len(applied) >= wanted:
            break
        result = TYPO_FUNCTIONS[name](current, rng)
        if result is None or result == current:
            continue
        current = result
        applied.append(name)
    return current, applied


def perturb_question(text: str, mode: str, seed: int, case_id: str) -> tuple[str, list[str]]:
    """Biến thể của một câu theo ``mode``; rng riêng theo (seed, id) nên không phụ thuộc thứ tự."""

    if mode == "none":
        return text, []
    if mode == "strip_all":
        return strip_all(text), ["strip_all"]
    if mode == "typo":
        return make_typo_variant(text, random.Random(f"{seed}:{case_id}"))
    raise ValueError(f"perturb mode không hợp lệ: {mode!r}")

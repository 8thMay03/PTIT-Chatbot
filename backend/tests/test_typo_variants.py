"""Bộ sinh biến thể lỗi gõ cho script đo bước sửa câu (scripts/typo_variants.py)."""

from __future__ import annotations

import json
import random
import unicodedata
from collections import Counter
from pathlib import Path

import pytest

from app.guardrails.normalization import strip_accents
from scripts.typo_variants import (
    TYPO_TYPES,
    char_noise,
    drop_punct,
    make_typo_variant,
    merge_words,
    perturb_question,
    strip_all,
    strip_partial,
    telex_leftover,
    to_telex,
    wrong_tone,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _has_loose_marks(text: str) -> bool:
    return any(unicodedata.category(char) == "Mn" for char in unicodedata.normalize("NFC", text))


def test_strip_all_removes_every_accent() -> None:
    assert strip_all("Học phí một tín chỉ là bao nhiêu?") == "Hoc phi mot tin chi la bao nhieu?"


def test_strip_partial_keeps_some_accents() -> None:
    text = "học phí một tín chỉ là bao nhiêu"
    result = strip_partial(text, random.Random(1))

    assert result != text
    assert result != strip_accents(text)
    assert strip_accents(result) == strip_accents(text)
    assert strip_partial("học", random.Random(1)) is None


@pytest.mark.parametrize(
    ("word", "telex"),
    [("học", "hocj"), ("phí", "phis"), ("nhiêu", "nhieeu"), ("được", "dduwowcj"), ("Đăng", "Ddawng"), ("ký", "kys")],
)
def test_to_telex(word, telex) -> None:
    assert to_telex(word) == telex


def test_telex_leftover_rewrites_one_accented_word() -> None:
    result = telex_leftover("học phí", random.Random(3))

    assert result in {"hocj phí", "học phis"}
    assert telex_leftover("hoc phi", random.Random(3)) is None


@pytest.mark.parametrize("seed", range(20))
def test_wrong_tone_changes_tone_of_one_word_and_composes(seed) -> None:
    text = "viện được nhiêu học"
    result = wrong_tone(text, random.Random(seed))

    assert result != text
    assert strip_accents(result) == strip_accents(text)
    assert not _has_loose_marks(result)
    assert sum(left != right for left, right in zip(result.split(), text.split())) == 1


def test_char_noise_changes_one_word_by_one_edit() -> None:
    text = "điều kiện tốt nghiệp"
    for seed in range(20):
        result = char_noise(text, random.Random(seed))
        if result is None:
            continue
        changed = [(a, b) for a, b in zip(result.split(), text.split()) if a != b]
        assert len(changed) == 1
        assert abs(len(changed[0][0]) - len(changed[0][1])) <= 1


def test_merge_words_joins_two_plain_words() -> None:
    assert merge_words("học phí", random.Random(0)) == "họcphí"
    assert merge_words("môn INT1340", random.Random(0)) is None


def test_drop_punct() -> None:
    assert drop_punct("Học phí, bao nhiêu?") == "Học phí bao nhiêu"
    assert drop_punct("Học phí bao nhiêu") is None


def test_codes_and_all_caps_words_are_never_perturbed() -> None:
    text = "Điểm môn INT1340 của K2024 tra trên QLDT, GPA bao nhiêu?"
    for seed in range(50):
        variant, _ = make_typo_variant(text, random.Random(seed))
        for token in ("INT1340", "K2024", "QLDT", "GPA"):
            assert token in variant.split() or f"{token}," in variant.split()


def test_typo_variant_applies_one_to_three_distinct_types() -> None:
    variant, applied = make_typo_variant("Sinh viên được nghỉ học tạm thời khi nào?", random.Random(7))

    assert variant != "Sinh viên được nghỉ học tạm thời khi nào?"
    assert 1 <= len(applied) <= 3
    assert len(set(applied)) == len(applied)
    assert set(applied) <= set(TYPO_TYPES)


def test_perturb_question_is_deterministic_per_seed_and_id() -> None:
    question = "Điều kiện xét học bổng khuyến khích học tập là gì?"

    first = perturb_question(question, "typo", 42, "case-1")
    assert perturb_question(question, "typo", 42, "case-1") == first
    assert perturb_question(question, "none", 42, "case-1") == (question, [])
    assert perturb_question(question, "strip_all", 42, "case-1") == (strip_accents(question), ["strip_all"])
    with pytest.raises(ValueError):
        perturb_question(question, "unknown", 42, "case-1")


def test_typo_set_on_golden_fixture_covers_every_type() -> None:
    cases = json.loads((FIXTURES / "ptit_rag_300.json").read_text(encoding="utf-8"))
    counts: Counter[str] = Counter()
    for case in cases:
        variant, applied = perturb_question(case["question"], "typo", 20261121, case["id"])
        assert variant != case["question"]
        assert not _has_loose_marks(variant)
        counts.update(applied)

    assert set(counts) == set(TYPO_TYPES)
    assert min(counts.values()) >= 50

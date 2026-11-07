"""Kiểm tra chất lượng bộ testset retrieval `ptit_rag_300.json` (Sổ tay D26).

`eval_retrieval.py` tính trúng khi chỉ một `expected_terms` là chuỗi con của
context, nên một term ngắn hoặc phổ biến làm hit@k tăng giả. Phần tĩnh luôn
chạy; phần đối chiếu corpus cần bản converted Sổ tay D26 (thư mục
`backend/storage/` bị gitignore) và tự bỏ qua khi thiếu.
"""

import json
import re
from pathlib import Path

import pytest

from app.core.config import settings
from scripts.eval_retrieval import load_dataset, normalize_text

DATASET_PATH = Path(__file__).parent / "fixtures" / "ptit_rag_300.json"
HANDBOOK_NAME = "74650b2536daae9e462a2a074e0d38d72e176796aa198d1ac0dc00ec8633a946.md"
CASE_ID_RE = re.compile(r"^d26_g[1-6]_\d{3}$")

MIN_TERM_LENGTH = 6
# Một term chỉ được xuất hiện ở tối đa ngần này vùng của Sổ tay; các lần lặp
# cách nhau dưới REGION_GAP ký tự (ô gộp của cùng một bảng) tính là một vùng.
MAX_TERM_REGIONS = 3
REGION_GAP = 1000


def _load_cases() -> list[dict]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


CASES = _load_cases()


def test_dataset_has_300_well_formed_cases() -> None:
    assert len(CASES) == 300
    ids = [case["id"] for case in CASES]
    assert len(set(ids)) == len(ids)
    for case in CASES:
        assert CASE_ID_RE.match(case["id"]), case["id"]
        assert case["question"].strip(), case["id"]
        assert case["reference_answer"].strip(), case["id"]
        terms = case["expected_terms"]
        assert 1 <= len(terms) <= 5, case["id"]
        assert all(isinstance(term, str) and term.strip() for term in terms), case["id"]


def test_dataset_loads_with_eval_retrieval_schema() -> None:
    cases = load_dataset(DATASET_PATH)
    assert len(cases) == 300
    assert all(case["expected_terms"] for case in cases)


def test_questions_and_term_sets_are_unique() -> None:
    questions = [normalize_text(case["question"]) for case in CASES]
    assert len(set(questions)) == len(questions)

    seen: dict[frozenset[str], str] = {}
    for case in CASES:
        key = frozenset(normalize_text(term) for term in case["expected_terms"])
        assert key not in seen, f"{case['id']} trùng bộ term với {seen[key]}"
        seen[key] = case["id"]


def test_terms_are_not_too_short() -> None:
    short = [
        (case["id"], term)
        for case in CASES
        for term in case["expected_terms"]
        if len(normalize_text(term)) < MIN_TERM_LENGTH
    ]
    assert not short


@pytest.fixture(scope="module")
def handbook_body() -> str:
    path = Path(settings.converted_documents_path) / HANDBOOK_NAME
    if not path.is_file():
        pytest.skip(f"Thiếu bản converted Sổ tay D26 tại '{path}' (backend/storage/ bị gitignore).")
    text = path.read_text(encoding="utf-8")
    # Bỏ bảng mục lục đầu sổ tay: chunker đã lọc bảng này nên không tính.
    marker = "## LỜI NÓI ĐẦU"
    assert marker in text
    return normalize_text(text[text.index(marker):])


def _regions(starts: list[int]) -> int:
    return sum(1 for index, start in enumerate(starts) if index == 0 or start - starts[index - 1] > REGION_GAP)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_terms_are_specific_in_handbook(case: dict, handbook_body: str) -> None:
    for term in case["expected_terms"]:
        normalized = normalize_text(term)
        starts = [match.start() for match in re.finditer(re.escape(normalized), handbook_body)]
        assert starts, f"{term!r} không có trong Sổ tay"
        assert _regions(starts) <= MAX_TERM_REGIONS, f"{term!r} xuất hiện ở {_regions(starts)} vùng"
        whole = re.findall(r"(?<!\w)" + re.escape(normalized) + r"(?!\w)", handbook_body)
        # Ví dụ: "điểm r" khớp vào "điểm rèn luyện", "0,0" khớp vào "10,0".
        assert len(whole) == len(starts), f"{term!r} khớp vào giữa từ/số khác"

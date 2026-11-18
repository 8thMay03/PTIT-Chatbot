"""Kiểm tra bộ câu không có đáp án `ptit_no_answer_56.json` (RAG-18).

Bộ này đo tỉ lệ từ chối đúng của confidence gate. Phần tĩnh luôn chạy; phần đối
chiếu corpus cần bản converted Sổ tay D26 (thư mục `backend/storage/` bị
gitignore) và tự bỏ qua khi thiếu.
"""

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from app.core.config import settings
from app.guardrails import check_scope
from scripts.eval_retrieval import normalize_text

FIXTURES = Path(__file__).parent / "fixtures"
DATASET_PATH = FIXTURES / "ptit_no_answer_56.json"
ANSWERABLE_SETS = ("ptit_rag_300.json", "ptit_ragas_100.json")
HANDBOOK_NAME = "74650b2536daae9e462a2a074e0d38d72e176796aa198d1ac0dc00ec8633a946.md"
CASE_ID_RE = re.compile(r"^noans_\d{3}$")
CATEGORIES = {"in_domain_missing", "near_miss", "out_of_domain"}
MIN_CASES = 50


def _load(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


CASES = _load(DATASET_PATH.name)


def test_dataset_is_well_formed() -> None:
    assert len(CASES) >= MIN_CASES
    ids = [case["id"] for case in CASES]
    assert len(set(ids)) == len(ids)
    for case in CASES:
        assert CASE_ID_RE.match(case["id"]), case["id"]
        assert case["answerable"] is False, case["id"]
        assert case["category"] in CATEGORIES, case["id"]
        assert case["question"].strip(), case["id"]
        assert case["why_unanswerable"].strip(), case["id"]
        probes = case["probe_terms"]
        assert probes and all(isinstance(term, str) and term.strip() for term in probes), case["id"]
        assert "expected_terms" not in case, case["id"]


def test_every_category_is_represented() -> None:
    counts = Counter(case["category"] for case in CASES)
    assert counts["in_domain_missing"] >= 15
    assert counts["near_miss"] >= 10
    assert counts["out_of_domain"] >= 8


def test_questions_are_unique_and_disjoint_from_answerable_sets() -> None:
    questions = [normalize_text(case["question"]) for case in CASES]
    assert len(set(questions)) == len(questions)
    for name in ANSWERABLE_SETS:
        answerable = {normalize_text(case.get("question") or case.get("user_input") or "") for case in _load(name)}
        overlap = set(questions) & answerable
        assert not overlap, f"Trùng câu hỏi với {name}: {sorted(overlap)}"


def test_every_case_passes_the_scope_guardrail() -> None:
    # Guardrail chỉ chặn injection/tác vụ cấm; mọi câu phải tới gate để đo việc từ chối.
    blocked = [case["id"] for case in CASES if not check_scope(case["question"]).allowed]
    assert not blocked


@pytest.fixture(scope="module")
def handbook_body() -> str:
    path = Path(settings.converted_documents_path) / HANDBOOK_NAME
    if not path.is_file():
        pytest.skip(f"Thiếu bản converted Sổ tay D26 tại '{path}' (backend/storage/ bị gitignore).")
    return normalize_text(path.read_text(encoding="utf-8"))


def test_probe_terms_are_absent_from_handbook(handbook_body: str) -> None:
    present = [
        (case["id"], term)
        for case in CASES
        for term in case["probe_terms"]
        if normalize_text(term) in handbook_body
    ]
    assert not present

"""Schema test case v2 (`scripts.eval_dataset`): validate, khớp bằng chứng, đọc/chuyển v1."""

import copy
import json
from pathlib import Path

import pytest

from scripts.eval_dataset import (
    DatasetError,
    EvidenceGroup,
    all_groups_rank,
    case_to_v2,
    coverage_by_k,
    dataset_to_v2,
    first_hit,
    group_ranks,
    groups_from_terms,
    load_cases,
    main,
    parse_payload,
    slot_coverage,
)

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLE = FIXTURES / "eval_schema_v2_example.json"
V1_FIXTURES = (
    "data.json",
    "ptit_faq.json",
    "ptit_no_answer_56.json",
    "ptit_rag_300.json",
    "ptit_ragas_100.json",
    "table_questions.json",
)


def _payload(**case_overrides) -> dict:
    case = {
        "id": "q1",
        "query": "Học kỳ phụ được đăng ký tối đa bao nhiêu tín chỉ?",
        "query_type": "single_hop",
        "ground_truth": "Tối đa 12 tín chỉ.",
        "evidence": [{"terms": [["12 tín chỉ", "mười hai tín chỉ"]]}],
    }
    case.update(case_overrides)
    return {"schema_version": 2, "name": "t", "cases": [{k: v for k, v in case.items() if v is not None}]}


def _errors(payload: dict) -> str:
    with pytest.raises(DatasetError) as info:
        parse_payload(payload, origin="t.json")
    return str(info.value)


# ---------------------------------------------------------------------------
# Validate v2
# ---------------------------------------------------------------------------


def test_example_fixture_is_valid_v2() -> None:
    dataset = load_cases(EXAMPLE)

    assert dataset.schema_version == 2
    assert dataset.name == "eval_schema_v2_example"
    by_id = {case.id: case for case in dataset.cases}
    assert {case.query_type for case in dataset.cases} >= {"single_hop", "comparison", "multi_hop", "global"}
    multi_hop = by_id["ex_multi_hop_internship_july"]
    assert [(group.article, group.article_title, group.clause) for group in multi_hop.evidence] == [
        ("34", "Thực tập cuối khóa", "4"),
        ("34", "Thực tập cuối khóa", "3"),
    ]
    assert by_id["ex_global_registration_timeline"].evidence == ()
    unanswerable = by_id["ex_unanswerable_cutoff_score"]
    assert not unanswerable.answerable
    assert unanswerable.unanswerable_category == "in_domain_missing"
    assert unanswerable.probe_terms == ("điểm chuẩn",)
    assert by_id["ex_single_hop_engineer_min_credits"].source == "Sổ tay sinh viên D26 _1_.pdf"
    assert by_id["ex_single_hop_engineer_min_credits"].difficulty == "easy"


def test_minimal_v2_case_gets_defaults() -> None:
    case = parse_payload(_payload(query_type=None)).cases[0]

    assert case.query_type == "unknown"
    assert case.split == "unknown"
    assert case.answerable is True
    assert case.evidence == (EvidenceGroup(terms=(("12 tín chỉ", "mười hai tín chỉ"),)),)


def test_v2_rejects_unknown_keys_and_reports_case_id() -> None:
    message = _errors(_payload(expected_terms=["12 tín chỉ"]))
    assert "cases[0] (q1)" in message
    assert "expected_terms" in message

    payload = _payload()
    payload["cases"][0]["evidence"][0]["anchors"] = {"article": "Điều 12"}
    assert "anchors" in _errors(payload)

    payload = _payload()
    payload["extra"] = 1
    assert "header" in _errors(payload)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"query": "  "}, ".query"),
        ({"query_type": "factual"}, ".query_type"),
        ({"split": "train"}, ".split"),
        ({"ground_truth": None}, ".ground_truth"),
        ({"answerable": "yes"}, ".answerable"),
        ({"evidence": [{"terms": []}]}, "cần `terms` hoặc `anchor`"),
        ({"evidence": [{"terms": [["  "]]}]}, ".terms[0]"),
        ({"evidence": [{"terms": [[]]}]}, ".terms[0]"),
        ({"evidence": [{"anchor": {"article": "Khoản 3"}}]}, ".anchor.article"),
        ({"evidence": [{"anchor": {"article": "Điều 3", "clause": "a"}}]}, ".anchor.clause"),
        ({"query_type": "multi_hop"}, "cần ít nhất 2 nhóm"),
        ({"query_type": "comparison"}, "cần ít nhất 2 nhóm"),
        ({"required_claims": ["ok", ""]}, ".required_claims"),
        ({"reference_contexts": [{"page": 3}]}, ".content"),
        ({"reference_contexts": [{"content": "x", "page": "3"}]}, ".page"),
        ({"unanswerable": {"category": "x"}}, "chỉ dùng khi answerable = false"),
    ],
)
def test_v2_validation_errors(overrides: dict, expected: str) -> None:
    payload = _payload()
    case = payload["cases"][0]
    for key, value in overrides.items():
        if value is None:
            case.pop(key, None)
        else:
            case[key] = value
    assert expected in _errors(payload)


def test_v2_unanswerable_rules() -> None:
    ok = _payload(
        answerable=False,
        ground_truth=None,
        evidence=None,
        query_type=None,
        unanswerable={"category": "near_miss", "reason": "Không có trong Sổ tay."},
    )
    case = parse_payload(ok).cases[0]
    assert case.unanswerable_category == "near_miss"
    assert case.unanswerable_reason == "Không có trong Sổ tay."

    assert "unanswerable: bắt buộc" in _errors(_payload(answerable=False, evidence=None))
    assert "không có bằng chứng" in _errors(
        _payload(answerable=False, unanswerable={"category": "x"})
    )


def test_v2_multi_hop_without_evidence_is_judge_only() -> None:
    case = parse_payload(_payload(query_type="multi_hop", evidence=None, required_claims=["a", "b"])).cases[0]
    assert case.evidence == ()
    assert case.required_claims == ("a", "b")


def test_v2_rejects_duplicate_ids_and_wrong_version() -> None:
    payload = _payload()
    payload["cases"].append(copy.deepcopy(payload["cases"][0]))
    assert "trùng" in _errors(payload)

    payload = _payload()
    payload["schema_version"] = 3
    assert "schema_version 3" in _errors(payload)

    assert "cases" in _errors({"schema_version": 2, "cases": []})


def test_v2_error_message_lists_every_error() -> None:
    payload = _payload()
    payload["cases"] = [
        {"id": "a", "query": ""},
        {"id": "b", "query": "x", "query_type": "nope", "ground_truth": "y"},
    ]
    message = _errors(payload)
    assert "(a).query" in message
    assert "(b).query_type" in message


# ---------------------------------------------------------------------------
# Khớp bằng chứng
# ---------------------------------------------------------------------------


def test_group_requires_every_slot_and_accepts_alternatives() -> None:
    group = EvidenceGroup(terms=(("16 tín chỉ", "mười sáu tín chỉ"), ("kỹ sư",)))
    contexts = [
        {"text": "Chương trình cử nhân: 15 tín chỉ."},
        {"text": "Chương trình KỸ SƯ: tối thiểu mười sáu tín chỉ."},
        {"text": "kỹ sư 16 tín chỉ"},
    ]

    assert group_ranks(contexts, [group]) == [(2, "mười sáu tín chỉ + kỹ sư")]
    assert group_ranks(contexts[:1], [group]) == [(None, None)]


def test_first_hit_all_groups_and_coverage() -> None:
    groups = (EvidenceGroup(terms=(("25 tín chỉ",),)), EvidenceGroup(terms=(("12 tín chỉ",),)))
    contexts = [
        {"text": "khác"},
        {"text": "Kỳ phụ tối đa 12 tín chỉ."},
        {"text": ""},
        {"text": "Kỳ chính tối đa 25 tín chỉ."},
    ]
    ranks = group_ranks(contexts, groups)

    assert ranks == [(4, "25 tín chỉ"), (2, "12 tín chỉ")]
    assert first_hit(ranks) == (2, "12 tín chỉ")
    assert all_groups_rank(ranks) == 4
    assert coverage_by_k(ranks, (1, 2, 4)) == {"coverage@1": 0.0, "coverage@2": 0.5, "coverage@4": 1.0}
    assert all_groups_rank(group_ranks(contexts[:2], groups)) is None
    assert all_groups_rank([]) is None
    assert coverage_by_k([], (1,)) == {"coverage@1": 0.0}


def test_first_hit_ties_prefer_earlier_group() -> None:
    groups = groups_from_terms(["b", "a"])
    assert first_hit(group_ranks([{"text": "a b"}], groups)) == (1, "b")


def test_anchor_uses_legal_metadata_and_article_title() -> None:
    contexts = [
        {"text": "1. Khoản một", "legal_article": "Điều 12. Thu học phí", "legal_clauses": ["1"]},
        {"text": "3. Khối lượng", "legal_article": "Điều 12. Đăng ký học tập", "legal_clauses": ["3"]},
        {"text": "4. Đợt", "legal_article": "Điều 12. Đăng ký học tập", "legal_clauses": ["4", "5"]},
    ]

    by_number = EvidenceGroup(article="12")
    by_title = EvidenceGroup(article="12", article_title="Đăng ký học tập")
    by_clause = EvidenceGroup(article="12", article_title="đăng ký học tập", clause="5")
    wrong = EvidenceGroup(article="13")

    assert group_ranks(contexts, [by_number, by_title, by_clause, wrong]) == [
        (1, "Điều 12"),
        (2, "Điều 12. Đăng ký học tập"),
        (3, "Điều 12. đăng ký học tập khoản 5"),
        (None, None),
    ]


def test_anchor_and_terms_must_both_match() -> None:
    group = EvidenceGroup(terms=(("12 tín chỉ",),), article="12")
    contexts = [
        {"text": "tối đa 12 tín chỉ", "legal_article": "Điều 10. Lớp học", "legal_clauses": []},
        {"text": "tối đa 12 tín chỉ", "legal_article": "Điều 12. Đăng ký", "legal_clauses": []},
    ]
    assert group_ranks(contexts, [group]) == [(2, "12 tín chỉ")]


def test_anchor_falls_back_to_extracting_from_heading() -> None:
    # Chunk cũ chưa có khóa legal_* (trước RAG-22): Điều lấy từ heading/section_path.
    context = {"text": "1. Nội dung khoản một.", "heading": "Điều 7. Học phí", "section_path": "Chương II"}
    assert group_ranks([context], [EvidenceGroup(article="7", clause="1")]) == [(1, "Điều 7 khoản 1")]


def test_doc_id_matches_source_name_ignoring_case_and_extension() -> None:
    contexts = [
        {"text": "học phí", "source_name": "Quy chế khác.pdf"},
        {"text": "học phí", "source_name": "Sổ tay sinh viên D26 _1_.pdf"},
    ]
    group = EvidenceGroup(terms=(("học phí",),), doc_id="sổ tay sinh viên d26 _1_")
    assert group_ranks(contexts, [group]) == [(2, "học phí")]


def test_slot_coverage_for_answers() -> None:
    slots = (("16 tín chỉ", "mười sáu tín chỉ"), ("25 tín chỉ",))
    assert slot_coverage("Tối thiểu mười sáu tín chỉ.", slots) == 0.5
    assert slot_coverage("16 tín chỉ và 25 tín chỉ", slots) == 1.0
    assert slot_coverage("bất kỳ", ()) == 1.0


# ---------------------------------------------------------------------------
# Đọc v1 và convert
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", V1_FIXTURES)
def test_every_v1_fixture_loads(name: str) -> None:
    dataset = load_cases(FIXTURES / name, require_evidence=False)
    assert dataset.schema_version == 1
    assert dataset.cases
    assert all(case.query for case in dataset.cases)


def test_v1_evidence_modes() -> None:
    raw = [{"id": "q", "question": "?", "expected_terms": ["450", " ", "TOEIC"], "source": "faq"}]

    per_term = parse_payload(raw).cases[0]
    single = parse_payload(raw, v1_evidence="single_group").cases[0]

    assert per_term.evidence == (EvidenceGroup(terms=(("450",),)), EvidenceGroup(terms=(("TOEIC",),)))
    assert single.evidence == (EvidenceGroup(terms=(("450",), ("TOEIC",))),)
    assert per_term.answer_slots == single.answer_slots == (("450",), ("TOEIC",))
    assert per_term.source == "faq"
    with pytest.raises(ValueError):
        parse_payload(raw, v1_evidence="any")


def test_v1_requires_terms_only_when_asked() -> None:
    raw = [{"id": "r1", "user_input": "Hỏi?", "reference": "Đáp.", "reference_context": "Ngữ cảnh."}]

    with pytest.raises(DatasetError, match="expected_terms"):
        parse_payload(raw)
    case = parse_payload(raw, require_evidence=False).cases[0]
    assert case.ground_truth == "Đáp."
    assert case.reference_contexts == ({"content": "Ngữ cảnh."},)

    blank = [{"id": "b", "question": "?", "expected_terms": ["   "]}]
    with pytest.raises(DatasetError, match="expected_terms"):
        parse_payload(blank)


def test_v1_unanswerable_rows_need_no_terms() -> None:
    raw = [
        {"id": "n", "question": "?", "answerable": False, "category": "near_miss", "probe_terms": ["phí"]},
    ]
    case = parse_payload(raw).cases[0]
    assert not case.answerable
    assert case.evidence == ()
    assert case.unanswerable_category == "near_miss"


@pytest.mark.parametrize("name", V1_FIXTURES)
def test_convert_v1_round_trips_evidence(name: str) -> None:
    v1 = load_cases(FIXTURES / name, require_evidence=False)
    v2 = parse_payload(dataset_to_v2(v1), origin="converted.json")

    assert v2.schema_version == 2
    assert len(v2.cases) == len(v1.cases)
    for before, after in zip(v1.cases, v2.cases):
        assert after.id == before.id
        assert after.query == before.query
        assert after.evidence == before.evidence
        assert after.answerable == before.answerable
        assert after.ground_truth == before.ground_truth
        assert after.source == before.source
        assert after.unanswerable_category == before.unanswerable_category
        assert after.probe_terms == before.probe_terms
        assert after.difficulty == before.difficulty


def test_convert_keeps_unmapped_v1_values_in_metadata() -> None:
    raw = [
        {
            "id": "t",
            "question": "?",
            "expected_terms": ["x"],
            "reference_answer": "x",
            "question_type": "factual",
            "evidence": "Sổ tay, dòng 8398",
        }
    ]
    payload = case_to_v2(parse_payload(raw).cases[0])
    assert "query_type" not in payload
    assert payload["metadata"] == {"evidence": "Sổ tay, dòng 8398", "legacy_question_type": "factual"}


def test_cli_validate_and_convert(tmp_path, capsys) -> None:
    assert main(["validate", str(EXAMPLE), str(FIXTURES / "ptit_faq.json")]) == 0
    out = capsys.readouterr().out
    assert "v2, 6 câu" in out and "v1, 20 câu" in out

    target = tmp_path / "faq.v2.json"
    assert main(["convert", str(FIXTURES / "ptit_faq.json"), "--out", str(target)]) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == 2
    assert main(["convert", str(FIXTURES / "ptit_faq.json"), "--out", str(target)]) == 2
    assert main(["convert", str(EXAMPLE), "--out", str(tmp_path / "x.json")]) == 2

    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version": 2, "cases": [{"id": "a"}]}', encoding="utf-8")
    assert main(["validate", str(bad)]) == 1

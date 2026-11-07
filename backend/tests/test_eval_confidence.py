"""Phần tính toán thuần của `scripts/eval_confidence.py` (không cần DB/API)."""

from pathlib import Path

import pytest

from scripts.eval_confidence import (
    DEFAULT_UNANSWERABLE,
    case_groups,
    evaluate_decisions,
    histogram,
    legacy_gate,
    load_cases,
    neighborhood,
    percentile,
    summarize_signals,
    sweep_rule,
    top_signals,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _record(
    case_id: str,
    answerable: bool,
    vector: float | None,
    bm25_norm: float | None = None,
    *,
    dataset: str = "ptit_rag_300",
    category: str = "answerable",
    scope_allowed: bool = True,
    hit_rank: int | None = 1,
) -> dict:
    return {
        "id": case_id,
        "dataset": dataset if answerable else "ptit_no_answer_56",
        "answerable": answerable,
        "category": category if answerable else "in_domain_missing",
        "scope_allowed": scope_allowed,
        "first_hit_rank": hit_rank if answerable else None,
        "signals": {"vector": vector, "bm25": None, "bm25_norm": bm25_norm, "rerank": None},
    }


def test_top_signals_takes_max_and_keeps_missing_signals_as_none() -> None:
    contexts = [
        {"vector_score": 0.4, "bm25_score": 3.0, "bm25_norm_score": 0.2},
        {"vector_score": 0.6, "bm25_score": None, "bm25_norm_score": None},
    ]

    assert top_signals(contexts) == {"vector": 0.6, "bm25": 3.0, "bm25_norm": 0.2, "rerank": None}
    assert top_signals([]) == {"vector": None, "bm25": None, "bm25_norm": None, "rerank": None}


def test_legacy_gate_passes_on_either_signal() -> None:
    assert legacy_gate({"vector": 0.31, "bm25": None}, 0.30, 2.0)
    assert legacy_gate({"vector": None, "bm25": 2.5}, 0.30, 2.0)
    assert not legacy_gate({"vector": 0.29, "bm25": 1.0}, 0.30, 2.0)


def test_percentile_interpolates_like_numpy() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    assert percentile(values, 50) == pytest.approx(2.5)
    assert percentile(values, 0) == 1.0
    assert percentile(values, 100) == 4.0
    assert percentile([], 50) is None


def test_summarize_signals_counts_missing_values() -> None:
    records = [_record("a", True, 0.5, 0.3), _record("b", True, 0.7, None)]

    summary = summarize_signals(records)

    assert summary["vector"]["count"] == 2
    assert summary["bm25_norm"]["missing"] == 1
    assert summary["rerank"]["count"] == 0


def test_case_groups_split_datasets_hit_subset_and_categories() -> None:
    records = [
        _record("a", True, 0.5, hit_rank=2),
        _record("b", True, 0.5, hit_rank=7),
        _record("c", True, 0.5, dataset="ptit_ragas_100", hit_rank=None),
        _record("d", False, 0.3),
    ]

    groups = case_groups(records)

    assert [item["id"] for item in groups["ptit_rag_300"]] == ["a", "b"]
    assert [item["id"] for item in groups["ptit_rag_300@hit4"]] == ["a"]
    assert "ptit_ragas_100@hit4" not in groups
    assert [item["id"] for item in groups["no_answer:in_domain_missing"]] == ["d"]


def test_evaluate_decisions_separates_gate_only_and_end_to_end() -> None:
    records = [
        _record("a1", True, 0.6),
        _record("a2", True, 0.4),
        _record("a3", True, 0.7, scope_allowed=False),
        _record("u1", False, 0.3),
        _record("u2", False, 0.55),
        _record("u3", False, 0.6, scope_allowed=False),
    ]

    metrics = evaluate_decisions(records, lambda record: record["signals"]["vector"] >= 0.5)

    # Gate-only: chỉ a2 bị gate từ chối; e2e: thêm a3 bị scope chặn.
    assert metrics["false_refusal"]["ptit_rag_300"] == pytest.approx(1 / 3, abs=1e-6)
    assert metrics["false_refusal_e2e"]["ptit_rag_300"] == pytest.approx(2 / 3, abs=1e-6)
    # Câu không có đáp án: u3 bị scope chặn nên không tính vào gate-only.
    assert metrics["unanswerable_in_scope"] == 2
    assert metrics["refusal_gate"] == pytest.approx(0.5)
    assert metrics["refusal_e2e"] == pytest.approx(2 / 3, abs=1e-6)
    assert metrics["refusal_gate_by_category"] == {"in_domain_missing": 0.5}


def test_sweep_picks_highest_refusal_within_false_refusal_budget() -> None:
    answerable = [_record(f"a{index}", True, 0.50 + index * 0.01) for index in range(20)]
    unanswerable = [_record(f"u{index}", False, 0.30 + index * 0.01) for index in range(10)]

    result = sweep_rule(answerable + unanswerable, "vector", max_false_refusal=0.05)

    best = result["best"]
    # Ngưỡng 0.40–0.50 từ chối mọi câu không có đáp án mà chưa chạm câu có đáp án;
    # ngưỡng 0.51 vượt ngân sách 5% (1/20 câu bị từ chối là đúng 5%, vẫn đạt).
    assert best["false_refusal"]["ptit_rag_300"] <= 0.05
    assert best["refusal_gate"] == 1.0
    assert result["frontier"][0]["false_refusal"]["ptit_rag_300"] == 0.0


def test_sweep_reports_missing_signal_and_infeasible_budget() -> None:
    records = [_record("a", True, 0.5), _record("u", False, 0.6)]

    assert sweep_rule(records, "rerank") == {"rule": "rerank", "available": False}
    # Câu không có đáp án điểm cao hơn câu có đáp án: chỉ ngưỡng chấp nhận cả hai đạt ngân sách 0%.
    best = sweep_rule(records, "vector", max_false_refusal=0.0)["best"]
    assert best["refusal_gate"] == 0.0


def test_neighborhood_shifts_each_threshold_by_ten_percent() -> None:
    records = [_record("a", True, 0.5, 0.4), _record("u", False, 0.3, 0.1)]

    rows = neighborhood(records, "weighted", {"weight": 0.5, "threshold": 0.4})

    assert [row["params"]["threshold"] for row in rows] == [0.36, 0.44]
    assert all(row["params"]["weight"] == 0.5 for row in rows)


def test_histogram_clamps_values_into_bins() -> None:
    bins = histogram([0.0, 0.25, 0.5, 1.0, 1.5], bins=2, lower=0.0, upper=1.0)

    assert [count for _, _, count in bins] == [2, 3]


def test_load_cases_reads_answerable_and_unanswerable_sets() -> None:
    unanswerable = load_cases(DEFAULT_UNANSWERABLE)
    answerable = load_cases(FIXTURES / "ptit_rag_300.json")

    assert all(not case["answerable"] for case in unanswerable)
    assert {case["category"] for case in unanswerable} == {"in_domain_missing", "near_miss", "out_of_domain"}
    assert all(case["answerable"] and case["expected_terms"] for case in answerable)
    assert answerable[0]["dataset"] == "ptit_rag_300"

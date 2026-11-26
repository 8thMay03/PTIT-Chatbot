"""Phần tính toán thuần của `scripts/eval_confidence.py` (không cần DB/API)."""

from pathlib import Path

import pytest

from scripts.eval_confidence import (
    DEFAULT_UNANSWERABLE,
    build_summary,
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
        {"vector_score": 0.6, "bm25_score": None, "bm25_norm_score": None, "bm25_folded_norm_score": 0.5},
    ]

    assert top_signals(contexts) == {
        "vector": 0.6,
        "bm25": 3.0,
        "bm25_norm": 0.2,
        "bm25_folded_norm": 0.5,
        "rerank": None,
    }
    assert top_signals([]) == {
        "vector": None,
        "bm25": None,
        "bm25_norm": None,
        "bm25_folded_norm": None,
        "rerank": None,
    }


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
    assert all(case["answerable"] and case["evidence"] for case in answerable)
    assert all(case["evidence"] == () for case in unanswerable)
    assert answerable[0]["dataset"] == "ptit_rag_300"


def test_load_cases_reads_v2_and_skips_claim_only_cases() -> None:
    cases = load_cases(FIXTURES / "eval_schema_v2_example.json")
    by_id = {case["id"]: case for case in cases}

    assert "ex_global_registration_timeline" not in by_id
    assert by_id["ex_unanswerable_cutoff_score"]["category"] == "in_domain_missing"
    assert len(by_id["ex_multi_hop_internship_july"]["evidence"]) == 2


def test_rerank_rules_are_only_swept_for_cross_encoder_reports() -> None:
    records = [_record("a", True, 0.6, 0.5), _record("u", False, 0.4, 0.1)]
    for record, score in zip(records, (5.0, -3.0)):
        record["signals"]["rerank"] = score
        record["gate_legacy"] = True

    heuristic = build_summary({"cases": records, "reranker": {"enabled": True, "provider": "heuristic"}}, sweep=True)
    cross_encoder = build_summary(
        {"cases": records, "reranker": {"enabled": True, "provider": "cross-encoder"}}, sweep=True
    )

    assert heuristic["sweep"]["rerank"] == {"rule": "rerank", "available": False}
    assert heuristic["sweep"]["rerank_and_norm"]["available"] is False
    assert cross_encoder["sweep"]["rerank_and_norm"]["best"]["refusal_gate"] == 1.0


# ---------------------------------------------------------------------------
# Sửa câu bằng LLM + biến thể lỗi gõ (task 2026-11-21-llm-query-correction)
# ---------------------------------------------------------------------------


def _corrected_record(case_id, *, reason, strong, hit_rank=1, perturbations=(), answerable=True, elapsed=10.0,
                      scope_stage="original"):
    record = _record(case_id, answerable, 0.6, 0.5, hit_rank=hit_rank,
                     scope_allowed=scope_stage != "corrected")
    record["gate"] = {"strong": strong, "reason": "passed" if strong else "below_bm25_norm"}
    record["perturbations"] = list(perturbations)
    record["scope_stage"] = scope_stage
    record["question"] = f"cau {case_id}"
    record["correction"] = {
        "corrected": reason == "corrected",
        "reason": reason,
        "text": f"câu {case_id}" if reason == "corrected" else f"cau {case_id}",
        "llm_output": "",
        "elapsed_ms": elapsed,
    }
    return record


def test_correction_summary_counts_gate_hits_reasons_and_timing() -> None:
    from scripts.eval_confidence import correction_summary

    records = [
        _corrected_record("a", reason="corrected", strong=True, perturbations=["wrong_tone"], elapsed=10),
        _corrected_record("b", reason="unchanged", strong=True, hit_rank=7, perturbations=["drop_punct"], elapsed=20),
        _corrected_record("c", reason="too_different", strong=False, hit_rank=None,
                          perturbations=["wrong_tone", "merge_words"], elapsed=30),
        _corrected_record("d", reason="protected_token_changed", strong=False, elapsed=40),
        _corrected_record("e", reason="invalid_output", strong=True, elapsed=50),
        _corrected_record("f", reason="corrected", strong=True, answerable=False, scope_stage="corrected", elapsed=0),
    ]

    summary = correction_summary(records)

    rag = summary["by_dataset"]["ptit_rag_300"]
    assert rag["n"] == 5
    assert rag["gate_pass"] == 3
    assert rag["hit@4"] == 3  # a, d, e (rank 1); b rank 7; c không trúng
    assert rag["corrected"] == 1
    assert rag["rejected"] == {
        "condition_1_too_different": 1,
        "condition_2_protected_token_changed": 1,
        "condition_3_invalid_output": 1,
    }
    assert rag["elapsed_ms"]["median"] == 30.0
    assert rag["elapsed_ms"]["p95"] == 48.0
    no_answer = summary["by_dataset"]["ptit_no_answer_56"]
    assert no_answer["hit@4"] is None
    assert no_answer["blocked_after_correction"] == 1
    assert no_answer["gate_pass_e2e"] == 0
    assert set(summary["by_dataset"]) == {"ptit_rag_300", "ptit_no_answer_56", "ptit_no_answer_56:in_domain_missing"}
    by_type = summary["by_perturbation"]
    assert by_type["ptit_rag_300:wrong_tone"]["n"] == 2
    assert by_type["ptit_rag_300:wrong_tone"]["gate_pass"] == 1
    assert by_type["ptit_rag_300:merge_words"]["n"] == 1
    assert [case["id"] for case in summary["changed_cases"]] == ["a", "f"]


def test_apply_perturbation_keeps_original_question() -> None:
    from scripts.eval_retrieval import apply_perturbation as perturb_cases

    cases = load_cases(FIXTURES / "ptit_rag_300.json")[:5]

    assert perturb_cases(cases, "none", 1) is cases
    stripped = perturb_cases(cases, "strip_all", 1)
    assert [case["original_question"] for case in stripped] == [case["question"] for case in cases]
    assert all(case["perturbations"] == ["strip_all"] for case in stripped)
    typo_a = perturb_cases(cases, "typo", 7)
    assert typo_a == perturb_cases(cases, "typo", 7)
    assert all(case["question"] != case["original_question"] for case in typo_a)


def test_warm_cache_is_skipped_when_correction_uses_llm(monkeypatch) -> None:
    from scripts.eval_retrieval import uses_llm_queries, warm_cache_texts

    monkeypatch.setattr("app.core.config.settings.query_rewrite_use_llm", False)
    monkeypatch.setattr("app.core.config.settings.multi_query_use_llm", False)
    monkeypatch.setattr("app.core.config.settings.query_correction_enabled", True)

    assert uses_llm_queries() is True
    assert warm_cache_texts("full", ["hoc phi"]) == []
    assert warm_cache_texts("hybrid", ["hoc phi"]) == ["hoc phi"]

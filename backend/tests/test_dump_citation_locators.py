"""Unit test cho phần so sánh/phân loại của scripts.dump_citation_locators (không cần DB)."""

from scripts.dump_citation_locators import classify_change, diff_dumps, keeps_article_units


def _row(chunk_id: str, article=None, clauses=(), points=(), legal=False) -> dict:
    return {
        "chunk_id": chunk_id,
        "section_path": "Sổ tay > Mục",
        "article": article,
        "clauses": list(clauses),
        "points": list(points),
        "locator": article,
        "has_legal_metadata": legal,
    }


def test_classify_change_categories() -> None:
    assert classify_change(_row("a", "Điều 5", ["1"]), _row("a", "Điều 5", ["1"])) == "unchanged"
    assert classify_change(_row("a", None, ["1", "2"], ["a"]), _row("a")) == "removed_non_article"
    assert (
        classify_change(_row("a", "Điều 5", [], ["b", "c"]), _row("a", "Điều 5", ["2"], ["b", "c"]))
        == "added_inherited_clause"
    )
    assert (
        classify_change(_row("a", "Điều 5", ["3"], ["a"]), _row("a", "Điều 5", ["2", "3"], ["a"]))
        == "added_inherited_clause"
    )
    assert (
        classify_change(_row("a", "Điều 5", ["1"], ["a"]), _row("a", "Điều 5", ["1", "2", "3"], ["a"]))
        == "added_inline_clause"
    )
    assert classify_change(_row("a", "Điều 5", ["3"]), _row("a", "Điều 5", ["2", "3", "4"])) == "added_inline_clause"
    # Mất Khoản trong Điều, đổi Điều, hoặc thêm Điều đều là "other".
    assert classify_change(_row("a", "Điều 5", ["1", "2"]), _row("a", "Điều 5", ["1"])) == "other"
    assert classify_change(_row("a", "Điều 5"), _row("a", "Điều 6")) == "other"
    assert classify_change(_row("a", None, ["1"]), _row("a", "Điều 6", ["1"])) == "other"


def test_keeps_article_units_only_constrains_article_rows() -> None:
    assert keeps_article_units(_row("a", None, ["1"]), _row("a"))
    assert keeps_article_units(_row("a", "Điều 5", ["1"]), _row("a", "Điều 5", ["2", "1"]))
    assert not keeps_article_units(_row("a", "Điều 5", ["1", "2"]), _row("a", "Điều 5", ["1"]))
    assert not keeps_article_units(_row("a", "Điều 5"), _row("a", None))


def test_diff_dumps_pairs_by_case_and_chunk() -> None:
    before = {
        "top_k": 2,
        "cases": [
            {"id": "q1", "contexts": [_row("c1", None, ["1"]), _row("c2", "Điều 5", ["1", "2"])]},
            {"id": "q2", "contexts": [_row("c1", None, ["1"]), _row("c3", "Điều 7")]},
            {"id": "q3", "contexts": [_row("c4")]},
        ],
    }
    after = {
        "top_k": 2,
        "cases": [
            {"id": "q1", "contexts": [_row("c2", "Điều 5", ["1"], legal=True), _row("c1", legal=True)]},
            {"id": "q2", "contexts": [_row("c1", legal=True), _row("c3", "Điều 7", legal=True)]},
        ],
    }

    diff = diff_dumps(before, after)

    assert diff["pairs"] == 4
    assert diff["counts"] == {
        "unchanged": 1,
        "removed_non_article": 2,
        "added_inherited_clause": 0,
        "added_inline_clause": 0,
        "other": 1,
    }
    assert diff["unique_changed_chunks"] == {
        "removed_non_article": 1,
        "added_inherited_clause": 0,
        "added_inline_clause": 0,
        "other": 1,
    }
    assert [(item["id"], item["chunk_id"]) for item in diff["ac05_violations"]] == [("q1", "c2")]
    assert diff["order_changed_cases"] == ["q1"]
    assert diff["unmatched"] == [{"id": "q3", "reason": "case_missing_after"}]
    assert diff["summary_after"]["with_legal_metadata"] == 4
    assert diff["summary_before"]["with_clauses_outside_article"] == 2

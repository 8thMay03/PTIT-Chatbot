"""Schema test case v2 dùng chung cho các script đánh giá RAG, kèm bộ đọc định dạng v1.

Đặc tả đầy đủ: ``documents/rag-eval/dataset-schema-v2.md``. Tóm tắt:

- File v2 là object ``{"schema_version": 2, "name", "corpus", "cases": [...]}``; mỗi câu có
  ``query``, ``query_type``, ``answerable``, ``split``, ``ground_truth``, ``required_claims``,
  ``evidence``, ``reference_contexts``, ``unanswerable``, ``metadata``. Khóa lạ bị từ chối.
- ``evidence`` là danh sách **nhóm bằng chứng**; mỗi bước suy luận một nhóm. Một context thỏa
  nhóm khi khớp ``doc_id`` (nếu có), neo Điều/Khoản (nếu có) **và** mọi slot trong ``terms``;
  mỗi slot là danh sách cách viết tương đương, khớp một là đủ.
- File v1 (mảng câu, hoặc object bọc ``data/samples/cases/questions``) được đọc như trước:
  ``expected_terms`` thành nhóm bằng chứng theo ngữ nghĩa của script gọi (``per_term``: mỗi term
  một nhóm — trúng khi một term xuất hiện, như ``eval_retrieval``; ``single_group``: mọi term là
  slot của một nhóm — một context phải chứa đủ, như ``evaluate.py``).

CLI::

    python -m scripts.eval_dataset validate tests/fixtures/*.json
    python -m scripts.eval_dataset convert tests/fixtures/ptit_faq.json --out ptit_faq.v2.json
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2
QUERY_TYPES = ("single_hop", "multi_hop", "comparison", "conditional", "aggregation", "global")
# Loại câu cần ít nhất hai nhóm bằng chứng khi có `evidence`.
MULTI_GROUP_QUERY_TYPES = ("multi_hop", "comparison")
SPLITS = ("dev", "test")
UNKNOWN = "unknown"
V1_EVIDENCE_MODES = ("per_term", "single_group")
V1_WRAPPER_KEYS = ("data", "samples", "cases", "questions")
MAX_REPORTED_ERRORS = 50

HEADER_KEYS = frozenset({"schema_version", "name", "description", "corpus", "cases"})
CASE_KEYS = frozenset(
    {
        "id",
        "query",
        "query_type",
        "answerable",
        "split",
        "ground_truth",
        "required_claims",
        "evidence",
        "reference_contexts",
        "unanswerable",
        "metadata",
    }
)
GROUP_KEYS = frozenset({"doc_id", "anchor", "terms", "note"})
ANCHOR_KEYS = frozenset({"article", "clause"})
UNANSWERABLE_KEYS = frozenset({"category", "reason", "probe_terms"})
REFERENCE_CONTEXT_KEYS = frozenset({"doc_id", "page", "chunk_id", "content"})
# Khóa v1 đã được ánh xạ sang trường v2; khóa còn lại giữ trong `metadata` khi convert.
V1_CONSUMED_KEYS = frozenset(
    {
        "id",
        "question",
        "user_input",
        "expected_terms",
        "answerable",
        "category",
        "why_unanswerable",
        "probe_terms",
        "reference_answer",
        "reference",
        "reference_context",
        "question_type",
        "difficulty",
        "source",
        "source_document",
        "document",
    }
)

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
ANCHOR_ARTICLE_RE = re.compile(r"^(?:điều\s+)?(\d+[a-z]?)\s*(?:[.:]\s*(.*))?$", re.IGNORECASE)
CONTEXT_ARTICLE_RE = re.compile(r"điều\s+(\d+[a-z]?)\b")
DOC_EXTENSION_RE = re.compile(r"\.(?:pdf|docx?|md|markdown|txt|html?)$")


class DatasetError(ValueError):
    """Dataset sai định dạng; thông điệp liệt kê lỗi theo id câu."""


# ---------------------------------------------------------------------------
# Mô hình dữ liệu
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceGroup:
    """Một bước bằng chứng: ``terms`` là các slot, mỗi slot là các cách viết tương đương."""

    terms: tuple[tuple[str, ...], ...] = ()
    article: str | None = None
    # Tên Điều (tùy chọn): một tài liệu có thể gồm nhiều quy chế đánh số Điều lại từ 1.
    article_title: str | None = None
    clause: str | None = None
    doc_id: str | None = None

    def article_label(self) -> str:
        return f"Điều {self.article}" + (f". {self.article_title}" if self.article_title else "")

    def describe(self) -> str:
        parts = []
        if self.doc_id:
            parts.append(self.doc_id)
        if self.article:
            parts.append(self.article_label() + (f" khoản {self.clause}" if self.clause else ""))
        parts.extend(" | ".join(slot) for slot in self.terms)
        return " / ".join(parts)


@dataclass(frozen=True)
class EvalCase:
    id: str
    query: str
    query_type: str = UNKNOWN
    answerable: bool = True
    split: str = UNKNOWN
    source: str = UNKNOWN
    evidence: tuple[EvidenceGroup, ...] = ()
    ground_truth: str = ""
    required_claims: tuple[str, ...] = ()
    reference_contexts: tuple[dict, ...] = ()
    unanswerable_category: str = ""
    unanswerable_reason: str = ""
    probe_terms: tuple[str, ...] = ()
    difficulty: str = ""
    # v1: `answer_terms` riêng của evaluate.py; v2 dùng các slot của `evidence`.
    answer_terms: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)

    @property
    def answer_slots(self) -> tuple[tuple[str, ...], ...]:
        """Các slot từ khóa phải có trong câu trả lời (mỗi slot khớp một cách viết là đủ)."""

        if self.answer_terms:
            return tuple((term,) for term in self.answer_terms)
        return tuple(slot for group in self.evidence for slot in group.terms)


@dataclass(frozen=True)
class Dataset:
    origin: str
    schema_version: int
    name: str
    cases: list[EvalCase]
    corpus: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Khớp bằng chứng với context retrieval (thuần, không cần DB)
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Chuẩn hóa để so khớp: NFKC, bỏ thẻ HTML, gộp khoảng trắng, casefold."""

    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    # NFKC trước để các ký tự full-width như ＜ trở thành < rồi mới lọc thẻ.
    normalized = HTML_TAG_RE.sub(" ", normalized)
    normalized = html.unescape(normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized)
    return normalized.casefold().strip()


@lru_cache(maxsize=8192)
def _normalized_term(term: str) -> str:
    return normalize_text(term)


def article_key(value: Any) -> tuple[str, str | None] | None:
    """``"Điều 12. Đăng ký học tập"`` → ``("12", "Đăng ký học tập")``; ``"Điều 12"``/``12`` →
    ``("12", None)``; giá trị khác → None."""

    text = WHITESPACE_RE.sub(" ", unicodedata.normalize("NFKC", str(value))).strip()
    match = ANCHOR_ARTICLE_RE.match(text)
    if not match:
        return None
    title = (match.group(2) or "").strip(" .:")
    return match.group(1).casefold(), title or None


def clause_key(value: Any) -> str | None:
    text = str(value).strip().rstrip(".")
    return str(int(text)) if text.isdigit() else None


def doc_key(value: Any) -> str:
    return DOC_EXTENSION_RE.sub("", normalize_text(str(value or "")))


class _PreparedContext:
    """Text chuẩn hóa + Điều/Khoản của một context, tính lười và dùng lại cho mọi nhóm."""

    def __init__(self, context: dict, text_field: str) -> None:
        self.context = context
        self.text = normalize_text(str(context.get(text_field) or ""))
        self._legal: tuple[str | None, str, frozenset[str]] | None = None
        self._doc: str | None = None

    @property
    def doc(self) -> str:
        if self._doc is None:
            self._doc = doc_key(self.context.get("source_name") or self.context.get("source"))
        return self._doc

    def legal(self) -> tuple[str | None, str, frozenset[str]]:
        if self._legal is None:
            context = self.context
            if "legal_clauses" in context:
                # Tính lúc chunking, có Khoản kế thừa từ chunk trước (RAG-22).
                article = context.get("legal_article")
                clauses = context.get("legal_clauses") or []
            else:
                # Chunk cũ chưa có khóa legal_*: tính lại như citation (import lười để module
                # không kéo app.ingestion khi chỉ validate/khớp term).
                from app.ingestion.legal_units import extract_legal_units

                units = extract_legal_units(
                    str(context.get("heading") or ""),
                    str(context.get("section_path") or ""),
                    str(context.get("evidence_text") or context.get("text") or ""),
                )
                article, clauses = units.article, units.clauses
            label = normalize_text(str(article or ""))
            match = CONTEXT_ARTICLE_RE.search(label)
            keys = frozenset(key for key in (clause_key(value) for value in clauses) if key)
            self._legal = (match.group(1) if match else None, label, keys)
        return self._legal


def _match_group(prepared: _PreparedContext, group: EvidenceGroup) -> str | None:
    """Nhãn phần khớp (các term gốc nối ``+``) nếu context thỏa nhóm, ngược lại None."""

    if not prepared.text:
        return None
    if group.doc_id and prepared.doc != doc_key(group.doc_id):
        return None
    if group.article:
        article, label, clauses = prepared.legal()
        if article != group.article or (group.article_title and _normalized_term(group.article_title) not in label):
            return None
        if group.clause and group.clause not in clauses:
            return None
    matched: list[str] = []
    for slot in group.terms:
        hit = next(
            (term for term in slot if (normalized := _normalized_term(term)) and normalized in prepared.text),
            None,
        )
        if hit is None:
            return None
        matched.append(hit)
    return " + ".join(matched) if matched else group.describe()


def group_ranks(
    contexts: list[dict],
    groups: tuple[EvidenceGroup, ...] | list[EvidenceGroup],
    text_field: str = "text",
) -> list[tuple[int | None, str | None]]:
    """Với từng nhóm: ``(rank bắt đầu từ 1 của context đầu tiên thỏa nhóm, nhãn khớp)``."""

    prepared = [_PreparedContext(context, text_field) for context in contexts]
    results: list[tuple[int | None, str | None]] = []
    for group in groups:
        found: tuple[int | None, str | None] = (None, None)
        for rank, item in enumerate(prepared, start=1):
            label = _match_group(item, group)
            if label is not None:
                found = (rank, label)
                break
        results.append(found)
    return results


def first_hit(ranks: list[tuple[int | None, str | None]]) -> tuple[int | None, str | None]:
    """Rank nhỏ nhất trong các nhóm; hòa thì lấy nhóm đứng trước (như duyệt term theo thứ tự)."""

    best: tuple[int | None, str | None] = (None, None)
    for rank, label in ranks:
        if rank is not None and (best[0] is None or rank < best[0]):
            best = (rank, label)
    return best


def all_groups_rank(ranks: list[tuple[int | None, str | None]]) -> int | None:
    """Rank nhỏ nhất mà top-k đã phủ đủ mọi nhóm; None nếu thiếu nhóm nào."""

    if not ranks or any(rank is None for rank, _ in ranks):
        return None
    return max(rank for rank, _ in ranks if rank is not None)


def coverage_by_k(
    ranks: list[tuple[int | None, str | None]],
    ks: tuple[int, ...],
) -> dict[str, float]:
    """coverage@k = số nhóm có context thỏa trong top-k / tổng số nhóm."""

    if not ranks:
        return {f"coverage@{k}": 0.0 for k in ks}
    return {
        f"coverage@{k}": round(sum(1 for rank, _ in ranks if rank is not None and rank <= k) / len(ranks), 6)
        for k in ks
    }


def slot_coverage(text: str, slots: tuple[tuple[str, ...], ...]) -> float:
    """Tỉ lệ slot có ít nhất một cách viết xuất hiện trong ``text`` (1.0 nếu không có slot)."""

    if not slots:
        return 1.0
    normalized = normalize_text(text)
    matched = sum(
        any((term_text := _normalized_term(term)) and term_text in normalized for term in slot)
        for slot in slots
    )
    return matched / len(slots)


def groups_from_terms(terms: list[str], mode: str = "per_term") -> tuple[EvidenceGroup, ...]:
    """``expected_terms`` v1 → nhóm bằng chứng; term rỗng sau chuẩn hóa bị bỏ."""

    if mode not in V1_EVIDENCE_MODES:
        raise ValueError(f"v1_evidence phải là một trong {V1_EVIDENCE_MODES}")
    kept = [str(term) for term in terms if normalize_text(str(term))]
    if not kept:
        return ()
    if mode == "per_term":
        return tuple(EvidenceGroup(terms=((term,),)) for term in kept)
    return (EvidenceGroup(terms=tuple((term,) for term in kept)),)


# ---------------------------------------------------------------------------
# Nạp dataset
# ---------------------------------------------------------------------------


def load_cases(
    path: Path,
    *,
    v1_evidence: str = "per_term",
    require_evidence: bool = True,
) -> Dataset:
    """Đọc file dataset v1 hoặc v2. Xem :func:`parse_payload`."""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetError(f"{path} không phải JSON hợp lệ: {exc}") from exc
    return parse_payload(payload, origin=str(path), v1_evidence=v1_evidence, require_evidence=require_evidence)


def parse_payload(
    payload: Any,
    *,
    origin: str = "<dataset>",
    v1_evidence: str = "per_term",
    require_evidence: bool = True,
) -> Dataset:
    """Nhận diện v1/v2 rồi chuẩn hóa về :class:`Dataset`.

    ``require_evidence`` chỉ áp dụng cho v1: câu có đáp án mà thiếu ``expected_terms`` thì
    báo lỗi (như các script cũ); ``evaluate_ragas`` tắt vì bộ Ragas chỉ có câu trả lời mẫu.
    v2 luôn validate đầy đủ theo đặc tả.
    """

    if v1_evidence not in V1_EVIDENCE_MODES:
        raise ValueError(f"v1_evidence phải là một trong {V1_EVIDENCE_MODES}")
    if isinstance(payload, dict) and "schema_version" in payload:
        if payload["schema_version"] != SCHEMA_VERSION:
            raise DatasetError(
                f"{origin}: schema_version {payload['schema_version']!r} không được hỗ trợ (chỉ {SCHEMA_VERSION})"
            )
        return _parse_v2(payload, origin)
    return _parse_v1(payload, origin, v1_evidence, require_evidence)


def _parse_v1(payload: Any, origin: str, v1_evidence: str, require_evidence: bool) -> Dataset:
    if isinstance(payload, dict):
        for key in V1_WRAPPER_KEYS:
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list) or not payload:
        raise DatasetError(f"{origin} phải chứa mảng câu hỏi không rỗng")

    cases: list[EvalCase] = []
    for number, raw in enumerate(payload, start=1):
        if not isinstance(raw, dict):
            raise DatasetError(f"Câu thứ {number} trong {origin} không phải object")
        query = str(raw.get("question") or raw.get("user_input") or "").strip()
        if not query:
            raise DatasetError(f"Câu thứ {number} trong {origin} thiếu `question`")
        case_id = str(raw.get("id") or f"case_{number:04d}")
        answerable = raw.get("answerable", True) is not False
        terms = raw.get("expected_terms") or []
        if isinstance(terms, str):
            terms = [terms]
        evidence = groups_from_terms(list(terms), v1_evidence) if answerable else ()
        if answerable and require_evidence and not evidence:
            raise DatasetError(f"Câu {case_id!r} thiếu `expected_terms`")
        reference_context = str(raw.get("reference_context") or "").strip()
        answer_terms = raw.get("answer_terms") or []
        cases.append(
            EvalCase(
                id=case_id,
                query=query,
                query_type=_first_value(raw, "question_type"),
                answerable=answerable,
                source=_first_value(raw, "source", "source_document", "document"),
                evidence=evidence,
                ground_truth=str(raw.get("reference_answer") or raw.get("reference") or "").strip(),
                reference_contexts=({"content": reference_context},) if reference_context else (),
                unanswerable_category="" if answerable else str(raw.get("category") or UNKNOWN),
                unanswerable_reason="" if answerable else str(raw.get("why_unanswerable") or ""),
                probe_terms=tuple(str(term) for term in raw.get("probe_terms") or []),
                difficulty=str(raw.get("difficulty") or "").strip(),
                answer_terms=tuple(str(term) for term in answer_terms),
                metadata={key: value for key, value in raw.items() if key not in V1_CONSUMED_KEYS},
            )
        )
    return Dataset(origin=origin, schema_version=1, name=Path(origin).stem, cases=cases)


def _first_value(raw: dict, *keys: str) -> str:
    for key in keys:
        value = str(raw.get(key) or "").strip()
        if value:
            return value
    return UNKNOWN


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _check_keys(raw: dict, allowed: frozenset[str], where: str, errors: list[str]) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        errors.append(f"{where}: khóa không hợp lệ {unknown}")


def _text_list(raw: Any, where: str, errors: list[str]) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(_is_text(item) for item in raw):
        errors.append(f"{where}: phải là mảng chuỗi không rỗng")
        return ()
    return tuple(item.strip() for item in raw)


def _parse_group(raw: Any, where: str, errors: list[str]) -> EvidenceGroup | None:
    if not isinstance(raw, dict):
        errors.append(f"{where}: nhóm bằng chứng phải là object")
        return None
    _check_keys(raw, GROUP_KEYS, where, errors)

    slots: list[tuple[str, ...]] = []
    terms = raw.get("terms", [])
    if not isinstance(terms, list):
        errors.append(f"{where}.terms: phải là mảng")
        terms = []
    for index, slot in enumerate(terms):
        alternatives = [slot] if isinstance(slot, str) else slot
        if (
            not isinstance(alternatives, list)
            or not alternatives
            or not all(_is_text(term) and normalize_text(term) for term in alternatives)
        ):
            errors.append(f"{where}.terms[{index}]: phải là chuỗi hoặc mảng chuỗi không rỗng")
            continue
        slots.append(tuple(alternatives))

    article = article_title = clause = None
    anchor = raw.get("anchor")
    if anchor is not None:
        if not isinstance(anchor, dict):
            errors.append(f"{where}.anchor: phải là object")
        else:
            _check_keys(anchor, ANCHOR_KEYS, f"{where}.anchor", errors)
            parsed = article_key(anchor.get("article", ""))
            if parsed is None:
                errors.append(f"{where}.anchor.article: cần dạng \"Điều 12\", \"Điều 12. <tên Điều>\" hoặc 12")
            else:
                article, article_title = parsed
            if anchor.get("clause") is not None:
                clause = clause_key(anchor["clause"])
                if clause is None:
                    errors.append(f"{where}.anchor.clause: phải là số Khoản")

    doc_id = raw.get("doc_id")
    if doc_id is not None and not _is_text(doc_id):
        errors.append(f"{where}.doc_id: phải là chuỗi không rỗng")
        doc_id = None
    if raw.get("note") is not None and not isinstance(raw.get("note"), str):
        errors.append(f"{where}.note: phải là chuỗi")
    if not slots and anchor is None:
        errors.append(f"{where}: nhóm cần `terms` hoặc `anchor`")
        return None
    return EvidenceGroup(
        terms=tuple(slots),
        article=article,
        article_title=article_title,
        clause=clause,
        doc_id=doc_id.strip() if doc_id else None,
    )


def _parse_reference_contexts(raw: Any, where: str, errors: list[str]) -> tuple[dict, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        errors.append(f"{where}: phải là mảng")
        return ()
    items: list[dict] = []
    for index, item in enumerate(raw):
        item_where = f"{where}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_where}: phải là object")
            continue
        _check_keys(item, REFERENCE_CONTEXT_KEYS, item_where, errors)
        if not _is_text(item.get("content")):
            errors.append(f"{item_where}.content: bắt buộc, là trích nguyên văn")
        if item.get("page") is not None and (not isinstance(item["page"], int) or isinstance(item["page"], bool)):
            errors.append(f"{item_where}.page: phải là số nguyên")
        for key in ("doc_id", "chunk_id"):
            if item.get(key) is not None and not _is_text(item[key]):
                errors.append(f"{item_where}.{key}: phải là chuỗi không rỗng")
        items.append(dict(item))
    return tuple(items)


def _parse_case(raw: Any, index: int, errors: list[str]) -> EvalCase | None:
    if not isinstance(raw, dict):
        errors.append(f"cases[{index}]: phải là object")
        return None
    where = f"cases[{index}]" + (f" ({raw['id']})" if _is_text(raw.get("id")) else "")
    _check_keys(raw, CASE_KEYS, where, errors)
    count_before = len(errors)

    case_id = raw.get("id")
    if not _is_text(case_id):
        errors.append(f"{where}.id: bắt buộc, là chuỗi không rỗng")
    query = raw.get("query")
    if not _is_text(query):
        errors.append(f"{where}.query: bắt buộc, là chuỗi không rỗng")
    query_type = raw.get("query_type", UNKNOWN)
    if "query_type" in raw and query_type not in QUERY_TYPES:
        errors.append(f"{where}.query_type: phải là một trong {list(QUERY_TYPES)}")
    answerable = raw.get("answerable", True)
    if not isinstance(answerable, bool):
        errors.append(f"{where}.answerable: phải là true/false")
        answerable = True
    split = raw.get("split", UNKNOWN)
    if "split" in raw and split not in SPLITS:
        errors.append(f"{where}.split: phải là một trong {list(SPLITS)}")
    ground_truth = raw.get("ground_truth", "")
    if not isinstance(ground_truth, str):
        errors.append(f"{where}.ground_truth: phải là chuỗi")
        ground_truth = ""
    required_claims = _text_list(raw.get("required_claims"), f"{where}.required_claims", errors)

    evidence_raw = raw.get("evidence", [])
    groups: list[EvidenceGroup] = []
    if not isinstance(evidence_raw, list):
        errors.append(f"{where}.evidence: phải là mảng")
    else:
        for group_index, group_raw in enumerate(evidence_raw):
            group = _parse_group(group_raw, f"{where}.evidence[{group_index}]", errors)
            if group is not None:
                groups.append(group)

    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        errors.append(f"{where}.metadata: phải là object")
        metadata = {}
    reference_contexts = _parse_reference_contexts(raw.get("reference_contexts"), f"{where}.reference_contexts", errors)

    category = reason = ""
    probe_terms: tuple[str, ...] = ()
    unanswerable = raw.get("unanswerable")
    if answerable:
        if not ground_truth.strip():
            errors.append(f"{where}.ground_truth: bắt buộc với câu có đáp án")
        if unanswerable is not None:
            errors.append(f"{where}.unanswerable: chỉ dùng khi answerable = false")
        if groups and query_type in MULTI_GROUP_QUERY_TYPES and len(groups) < 2:
            errors.append(f"{where}.evidence: query_type {query_type} cần ít nhất 2 nhóm bằng chứng")
    else:
        if evidence_raw:
            errors.append(f"{where}.evidence: câu không có đáp án không có bằng chứng")
        if required_claims:
            errors.append(f"{where}.required_claims: câu không có đáp án không có claim")
        if not isinstance(unanswerable, dict):
            errors.append(f"{where}.unanswerable: bắt buộc (object) khi answerable = false")
        else:
            _check_keys(unanswerable, UNANSWERABLE_KEYS, f"{where}.unanswerable", errors)
            category = unanswerable.get("category")
            if not _is_text(category):
                errors.append(f"{where}.unanswerable.category: bắt buộc")
                category = ""
            reason = unanswerable.get("reason", "")
            if not isinstance(reason, str):
                errors.append(f"{where}.unanswerable.reason: phải là chuỗi")
                reason = ""
            probe_terms = _text_list(unanswerable.get("probe_terms"), f"{where}.unanswerable.probe_terms", errors)

    if len(errors) > count_before:
        return None
    doc_ids = sorted({group.doc_id for group in groups if group.doc_id})
    source = " + ".join(doc_ids) or str(metadata.get("source") or "").strip() or UNKNOWN
    return EvalCase(
        id=case_id.strip(),
        query=query.strip(),
        query_type=query_type,
        answerable=answerable,
        split=split,
        source=source,
        evidence=tuple(groups),
        ground_truth=ground_truth.strip(),
        required_claims=required_claims,
        reference_contexts=reference_contexts,
        unanswerable_category=category.strip(),
        unanswerable_reason=reason.strip(),
        probe_terms=probe_terms,
        difficulty=str(metadata.get("difficulty") or "").strip(),
        metadata=dict(metadata),
    )


def _parse_v2(payload: dict, origin: str) -> Dataset:
    errors: list[str] = []
    _check_keys(payload, HEADER_KEYS, "header", errors)
    name = payload.get("name", Path(origin).stem)
    if not _is_text(name):
        errors.append("header.name: phải là chuỗi không rỗng")
        name = Path(origin).stem
    corpus = payload.get("corpus", {})
    if not isinstance(corpus, dict):
        errors.append("header.corpus: phải là object")
        corpus = {}
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        errors.append("header.cases: phải là mảng câu không rỗng")
        raw_cases = []

    cases: list[EvalCase] = []
    for index, raw in enumerate(raw_cases):
        case = _parse_case(raw, index, errors)
        if case is not None:
            cases.append(case)
    duplicates = sorted(case_id for case_id, count in Counter(case.id for case in cases).items() if count > 1)
    if duplicates:
        errors.append(f"id bị trùng: {duplicates}")
    if errors:
        shown = errors[:MAX_REPORTED_ERRORS]
        more = f"\n- … và {len(errors) - len(shown)} lỗi khác" if len(errors) > len(shown) else ""
        raise DatasetError(f"{origin}: {len(errors)} lỗi schema v2:\n- " + "\n- ".join(shown) + more)
    return Dataset(origin=origin, schema_version=SCHEMA_VERSION, name=name.strip(), cases=cases, corpus=dict(corpus))


# ---------------------------------------------------------------------------
# Ghi v2 (convert)
# ---------------------------------------------------------------------------


def group_to_v2(group: EvidenceGroup) -> dict:
    payload: dict[str, Any] = {}
    if group.doc_id:
        payload["doc_id"] = group.doc_id
    if group.article:
        payload["anchor"] = {"article": group.article_label()}
        if group.clause:
            payload["anchor"]["clause"] = group.clause
    if group.terms:
        payload["terms"] = [slot[0] if len(slot) == 1 else list(slot) for slot in group.terms]
    return payload


def case_to_v2(case: EvalCase) -> dict:
    """:class:`EvalCase` → object câu v2. Giá trị v1 không có chỗ trong v2 nằm ở ``metadata``."""

    metadata = dict(case.metadata)
    payload: dict[str, Any] = {"id": case.id, "query": case.query}
    if case.query_type in QUERY_TYPES:
        payload["query_type"] = case.query_type
    elif case.query_type != UNKNOWN:
        metadata["legacy_question_type"] = case.query_type
    payload["answerable"] = case.answerable
    if case.split in SPLITS:
        payload["split"] = case.split
    if case.ground_truth:
        payload["ground_truth"] = case.ground_truth
    if case.required_claims:
        payload["required_claims"] = list(case.required_claims)
    if case.evidence:
        payload["evidence"] = [group_to_v2(group) for group in case.evidence]
    if case.reference_contexts:
        payload["reference_contexts"] = [dict(item) for item in case.reference_contexts]
    if not case.answerable:
        unanswerable: dict[str, Any] = {"category": case.unanswerable_category or UNKNOWN}
        if case.unanswerable_reason:
            unanswerable["reason"] = case.unanswerable_reason
        if case.probe_terms:
            unanswerable["probe_terms"] = list(case.probe_terms)
        payload["unanswerable"] = unanswerable
    if case.difficulty:
        metadata["difficulty"] = case.difficulty
    if case.source != UNKNOWN and not any(group.doc_id for group in case.evidence):
        metadata["source"] = case.source
    if case.answer_terms:
        metadata["answer_terms"] = list(case.answer_terms)
    if metadata:
        payload["metadata"] = metadata
    return payload


def dataset_to_v2(dataset: Dataset, name: str | None = None) -> dict:
    payload: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "name": name or dataset.name}
    if dataset.corpus:
        payload["corpus"] = dict(dataset.corpus)
    payload["cases"] = [case_to_v2(case) for case in dataset.cases]
    return payload


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def summarize(dataset: Dataset) -> str:
    cases = dataset.cases

    def counts(values: list[str]) -> str:
        return ", ".join(f"{label} {count}" for label, count in sorted(Counter(values).items()))

    groups = Counter(len(case.evidence) for case in cases if case.answerable)
    return "\n".join(
        [
            f"{dataset.origin}: v{dataset.schema_version}, {len(cases)} câu, name={dataset.name}",
            f"  query_type: {counts([case.query_type for case in cases])}",
            f"  answerable: {counts(['true' if case.answerable else 'false' for case in cases])}",
            f"  split: {counts([case.split for case in cases])}",
            "  số nhóm bằng chứng (câu có đáp án): "
            + ", ".join(f"{size} nhóm {count}" for size, count in sorted(groups.items())),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Kiểm tra / chuyển dataset đánh giá sang schema v2.")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Kiểm tra file v1/v2 và in thống kê.")
    validate.add_argument("paths", nargs="+", type=Path)
    convert = commands.add_parser("convert", help="Chuyển file v1 sang v2 (mỗi expected_terms thành một nhóm).")
    convert.add_argument("path", type=Path)
    convert.add_argument("--out", type=Path, required=True)
    convert.add_argument("--name", help="Tên dataset (mặc định: tên file nguồn).")
    convert.add_argument("--force", action="store_true", help="Ghi đè file đích nếu đã có.")
    args = parser.parse_args(argv)

    if args.command == "validate":
        failed = 0
        for path in args.paths:
            try:
                print(summarize(load_cases(path, require_evidence=False)))
            except (OSError, DatasetError) as exc:
                failed += 1
                print(f"LỖI {exc}", file=sys.stderr)
        return 1 if failed else 0

    if args.out.exists() and not args.force:
        print(f"Lỗi: {args.out} đã tồn tại (dùng --force để ghi đè)", file=sys.stderr)
        return 2
    try:
        dataset = load_cases(args.path, require_evidence=False)
        if dataset.schema_version == SCHEMA_VERSION:
            print(f"Lỗi: {args.path} đã là schema v2", file=sys.stderr)
            return 2
        payload = dataset_to_v2(dataset, args.name)
        # Đảm bảo file ghi ra hợp lệ trước khi ghi.
        converted = parse_payload(payload, origin=str(args.out))
    except (OSError, DatasetError) as exc:
        print(f"LỖI {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(summarize(converted))
    print(f"Đã ghi {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

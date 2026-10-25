"""Kiểm tra chất lượng chunk trên toàn kho sau RAG-06 (AC-01…AC-04).

Quét index trong DB (mặc định) hoặc dry-run chunker trên một thư mục tài liệu
(không ghi DB). Mỗi phát hiện gắn mã lỗi:

- ``parent_spans_articles`` (lỗi): một parent chứa nội dung ≥ 2 Điều khác nhau.
- ``chunk_starts_mid_word`` (lỗi): chunk bắt đầu bằng chữ thường — dấu hiệu bị
  cắt giữa từ.
- ``chunk_too_short`` (lỗi): chunk ngắn hơn ``--min-chars`` (120) mà section/
  parent của nó không ngắn như vậy.
- ``noise_chunk`` (lỗi): chunk mục lục (chấm dẫn + số trang), quốc hiệu, khối
  chữ ký hoặc số trang còn sót trong index.
- ``search_text_missing_context`` (lỗi): ``search_text`` thiếu tên tài liệu hoặc
  ``section_path``.

Ví dụ::

    python -m scripts.check_chunks                       # quét DB
    python -m scripts.check_chunks --data ..\\data       # dry-run cả kho tài liệu
    python -m scripts.check_chunks --db --strict         # exit 1 khi có lỗi
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.cleaner import _drop_noise_lines, is_noise_line

ERROR_CODES = frozenset(
    {
        "parent_spans_articles",
        "chunk_starts_mid_word",
        "chunk_too_short",
        "noise_chunk",
        "search_text_missing_context",
    }
)
DEFAULT_MIN_CHARS = 120

# Chunk bắt đầu bằng chữ thường (không phải đầu từ) — regex chữ thường tiếng Việt.
_LOWERCASE_START = re.compile(r"^[a-zà-ỹ]")
# Heading "Điều N." ở đầu dòng trong parent (post RAG-05 mọi Điều đều là heading).
_ARTICLE_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+Điều\s+\d+\s*[.:]?", re.IGNORECASE)
_ATX_PREFIX = re.compile(r"^\s{0,3}#{1,6}\s+")
_MAX_FINDINGS_PER_CODE = 20


@dataclass(frozen=True)
class Finding:
    code: str
    ref: str
    message: str

    @property
    def is_error(self) -> bool:
        return self.code in ERROR_CODES


def check_parent_spans_articles(ref: str, parent_text: str) -> Finding | None:
    """AC-01: một parent chỉ được chứa nội dung của một Điều."""
    count = sum(
        1
        for line in parent_text.splitlines()
        if _ARTICLE_HEADING.match(line)
    )
    if count > 1:
        return Finding("parent_spans_articles", ref, f"parent chứa {count} heading Điều")
    return None


def check_mid_word_start(ref: str, text: str) -> Finding | None:
    """AC-02: chunk không được bắt đầu giữa từ."""
    if _LOWERCASE_START.match(text):
        return Finding("chunk_starts_mid_word", ref, f"bắt đầu chữ thường: {text[:40]!r}")
    return None


def check_short_chunk(ref: str, text: str, parent_text: str, min_chars: int) -> Finding | None:
    """AC-02: chunk < min_chars chỉ hợp lệ khi cả section (parent) cũng ngắn.

    Đo phần thân parent (bỏ dòng heading đầu) — nhỏ hơn min_chars nghĩa là
    section quá ngắn để gộp thêm.
    """
    if len(text) >= min_chars:
        return None
    parent_lines = parent_text.splitlines()
    parent_body = "\n".join(parent_lines[1:]) if _ATX_PREFIX.match(parent_lines[0] or "") else parent_text
    if len(parent_body.strip()) < min_chars:
        return None
    return Finding("chunk_too_short", ref, f"{len(text)} ký tự (parent thân {len(parent_body.strip())} ký tự)")


def check_noise_chunk(ref: str, text: str) -> Finding | None:
    """AC-03: index không còn chunk mục lục/quốc hiệu/chữ ký/số trang.

    Hai đường phát hiện: từng dòng khớp mẫu nhiễu, hoặc chunk mà cleaner sẽ
    cắt bỏ một phần nội dung (section "MỤC LỤC" còn sót là trường hợp điển hình).
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|"):
            continue
        if is_noise_line(stripped):
            return Finding("noise_chunk", ref, f"dòng nhiễu: {stripped[:60]!r}")

    kept = [line for line in _drop_noise_lines(text.splitlines()) if line.strip()]
    original = [line for line in text.splitlines() if line.strip()]
    if original and len(kept) < len(original):
        dropped = [line.strip() for line in original if line not in kept]
        sample = dropped[0][:60] if dropped else ""
        return Finding("noise_chunk", ref, f"cleaner sẽ bỏ {len(original) - len(kept)} dòng: {sample!r}")
    return None


def check_search_text(ref: str, search_text: str, document_title: str, section_path: str) -> Finding | None:
    """AC-04: search_text phải chứa tên tài liệu và section_path."""
    if not search_text:
        return Finding("search_text_missing_context", ref, "search_text rỗng")
    missing = []
    if document_title and document_title.strip() not in search_text:
        missing.append("tên tài liệu")
    if section_path and section_path.strip() not in search_text:
        missing.append("section_path")
    if missing:
        return Finding("search_text_missing_context", ref, f"thiếu {' + '.join(missing)}")
    return None


@dataclass
class ChunkView:
    """Thông tin tối thiểu script cần cho mỗi chunk con (từ DB hoặc dry-run)."""

    ref: str
    document_title: str
    text: str
    search_text: str
    section_path: str
    parent_ref: str
    parent_text: str


def check_chunks(views: list[ChunkView], min_chars: int = DEFAULT_MIN_CHARS) -> list[Finding]:
    findings: list[Finding] = []
    seen_parents: set[str] = set()
    for view in views:
        if view.parent_ref not in seen_parents:
            seen_parents.add(view.parent_ref)
            finding = check_parent_spans_articles(view.parent_ref, view.parent_text)
            if finding:
                findings.append(finding)
        for checker in (
            lambda: check_mid_word_start(view.ref, view.text),
            lambda: check_short_chunk(view.ref, view.text, view.parent_text, min_chars),
            lambda: check_noise_chunk(view.ref, view.text),
            lambda: check_search_text(view.ref, view.search_text, view.document_title, view.section_path),
        ):
            finding = checker()
            if finding:
                findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# Nguồn dữ liệu: DB hoặc dry-run
# ---------------------------------------------------------------------------


def views_from_db() -> tuple[list[ChunkView], dict]:
    from sqlalchemy import select

    from app.db.models import Chunk, Document
    from app.db.session import SessionLocal

    views: list[ChunkView] = []
    with SessionLocal() as session:
        documents = {
            document.id: (document.title or Path(document.source_path).stem)
            for document in session.scalars(select(Document))
        }
        stats = {"documents": len(documents), "chunks": 0}
        for chunk in session.scalars(select(Chunk).order_by(Chunk.document_id, Chunk.chunk_index)):
            metadata = chunk.chunk_metadata or {}
            stats["chunks"] += 1
            views.append(
                ChunkView(
                    ref=chunk.id,
                    document_title=documents.get(chunk.document_id, ""),
                    text=chunk.text,
                    search_text=chunk.search_text or "",
                    section_path=str(metadata.get("section_path") or ""),
                    parent_ref=str(metadata.get("parent_id") or chunk.id),
                    parent_text=str(metadata.get("parent_text") or chunk.text),
                )
            )
    return views, stats


def views_from_data(data_dir: Path) -> tuple[list[ChunkView], dict]:
    """Dry-run: chạy đúng lộ trình ingest (parser + chunker) nhưng không ghi DB."""
    from app.core.config import settings
    from app.ingestion.loaders import load_documents
    from app.ingestion.pipeline import _records_for_document

    views: list[ChunkView] = []
    stats = {"documents": 0, "chunks": 0}
    for document in load_documents(data_dir):
        record, chunk_records, _payload = _records_for_document(document)
        stats["documents"] += 1
        for chunk_record in chunk_records:
            metadata = chunk_record.metadata or {}
            stats["chunks"] += 1
            views.append(
                ChunkView(
                    ref=chunk_record.id,
                    document_title=record.title or document.path.stem,
                    text=chunk_record.text,
                    search_text=chunk_record.search_text,
                    section_path=str(metadata.get("section_path") or ""),
                    parent_ref=str(metadata.get("parent_id") or chunk_record.id),
                    parent_text=str(metadata.get("parent_text") or chunk_record.text),
                )
            )
    stats["settings"] = {
        "parent_size": settings.chunk_size,
        "child_size": settings.child_chunk_size,
        "min_child_chars": settings.min_child_chunk_chars,
    }
    return views, stats


def print_report(views: list[ChunkView], findings: list[Finding], min_chars: int) -> None:
    parents = {view.parent_ref for view in views}
    by_code: dict[str, list[Finding]] = {}
    for finding in findings:
        by_code.setdefault(finding.code, []).append(finding)

    print(f"chunks={len(views)} parents={len(parents)} min_chars={min_chars}")
    if not findings:
        print("OK: không phát hiện vi phạm.")
        return
    for code in sorted(by_code):
        items = by_code[code]
        print(f"\n[{code}] {len(items)} vi phạm")
        for finding in items[:_MAX_FINDINGS_PER_CODE]:
            print(f"  - {finding.ref}: {finding.message}")
        if len(items) > _MAX_FINDINGS_PER_CODE:
            print(f"  … và {len(items) - _MAX_FINDINGS_PER_CODE} vi phạm khác")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kiểm tra chất lượng chunk trên toàn kho (RAG-06).")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--db", action="store_true", help="Quét index trong DB (mặc định).")
    source.add_argument("--data", type=Path, help="Dry-run chunker trên thư mục tài liệu, không ghi DB.")
    parser.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS, help="Ngưỡng chunk ngắn (mặc định 120).")
    parser.add_argument("--strict", action="store_true", help="Trả mã 1 khi có lỗi.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.data is not None:
        backend_dir = Path(__file__).resolve().parents[1]
        data_dir = args.data if args.data.is_absolute() else (backend_dir / args.data).resolve()
        views, stats = views_from_data(data_dir)
    else:
        views, stats = views_from_db()

    findings = check_chunks(views, min_chars=args.min_chars)
    print(f"nguồn={'data/' + str(args.data) if args.data else 'db'} documents={stats['documents']}")
    print_report(views, findings, args.min_chars)
    has_errors = any(finding.is_error for finding in findings)
    if args.strict and has_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

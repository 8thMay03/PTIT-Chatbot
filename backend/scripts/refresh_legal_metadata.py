"""Ghi Điều/Khoản/Điểm (``legal_*``) vào metadata chunk đã index mà không chunk lại/embed lại (RAG-22).

Chunk index trước RAG-22 không có các khóa ``legal_article``, ``legal_clauses``,
``legal_points``; citation khi đó tự tính lại nhưng không biết Khoản đang mở của chunk
bắt đầu giữa Khoản. Script chia lại ``parsed_text`` đã lưu bằng đúng ``_chunk_records``
của pipeline (cùng điều kiện khớp với ``refresh_search_text``: tập id chunk và ``text``
từng chunk phải khớp DB, lệch thì bỏ qua tài liệu đó) rồi gộp các khóa ``legal_*`` vào
metadata hiện có. Không ghi ``text``, ``search_text``, vector hay khóa metadata khác.

BM25 tự dựng lại trong tiến trình mới; backend đang chạy cần khởi động lại để chỉ mục
BM25 trong bộ nhớ đọc metadata mới.

Ví dụ::

    python -m scripts.refresh_legal_metadata            # dry-run: chỉ báo cáo
    python -m scripts.refresh_legal_metadata --apply    # ghi metadata
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, undefer

from app.db.models import Chunk, Document
from app.ingestion.legal_units import LEGAL_METADATA_KEYS
from scripts.refresh_search_text import rechunk_matching_db


@dataclass
class DocumentLegalRefresh:
    document_id: str
    title: str
    chunks: int
    changed: int = 0
    with_article: int = 0
    with_clauses: int = 0
    skipped_reason: str = ""


@dataclass
class LegalRefreshReport:
    documents: list[DocumentLegalRefresh] = field(default_factory=list)
    updates: dict[str, dict] = field(default_factory=dict)

    @property
    def changed(self) -> int:
        return sum(item.changed for item in self.documents)

    @property
    def skipped(self) -> list[DocumentLegalRefresh]:
        return [item for item in self.documents if item.skipped_reason]


def plan_refresh(session: Session) -> LegalRefreshReport:
    """Tính khóa ``legal_*`` cho mọi chunk của tài liệu có ``parsed_text`` khớp DB."""
    report = LegalRefreshReport()
    documents = session.scalars(
        select(Document).options(undefer(Document.parsed_text)).order_by(Document.id)
    ).all()
    for document in documents:
        rows = session.scalars(select(Chunk).where(Chunk.document_id == document.id)).all()
        item = DocumentLegalRefresh(document.id, document.title or "", len(rows))
        report.documents.append(item)
        records, item.skipped_reason = rechunk_matching_db(document, rows)
        if item.skipped_reason:
            continue
        by_id = {row.id: row for row in rows}
        for record in records:
            legal = {key: record.metadata[key] for key in LEGAL_METADATA_KEYS}
            item.with_article += bool(legal["legal_article"])
            item.with_clauses += bool(legal["legal_clauses"])
            current = by_id[record.id].chunk_metadata or {}
            if any(key not in current or current[key] != legal[key] for key in LEGAL_METADATA_KEYS):
                item.changed += 1
                report.updates[record.id] = legal
    return report


def apply_refresh(session: Session, updates: dict[str, dict]) -> int:
    """Gộp khóa ``legal_*`` vào metadata hiện có, giữ mọi khóa khác."""
    for chunk_id, legal in updates.items():
        chunk = session.get(Chunk, chunk_id)
        # Gán dict mới: cột JSON không theo dõi thay đổi tại chỗ.
        chunk.chunk_metadata = {**(chunk.chunk_metadata or {}), **legal}
    session.commit()
    return len(updates)


def format_report(report: LegalRefreshReport) -> str:
    lines: list[str] = []
    for item in report.documents:
        if item.skipped_reason:
            lines.append(f"- {item.document_id} ({item.title}): BỎ QUA — {item.skipped_reason}")
            continue
        lines.append(
            f"- {item.document_id} ({item.title}): {item.chunks} chunk, {item.changed} cần ghi legal_*; "
            f"{item.with_article} có Điều, {item.with_clauses} có Khoản"
        )
    lines.append(
        f"Tổng: {len(report.documents)} tài liệu, {report.changed} chunk cần ghi, "
        f"{len(report.skipped)} tài liệu bỏ qua."
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ghi Điều/Khoản/Điểm vào metadata chunk trong DB (không chunk lại, không embedding)."
    )
    parser.add_argument("--apply", action="store_true", help="Ghi vào DB (mặc định chỉ dry-run).")
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None, session_factory: Callable[[], Session] | None = None
) -> int:
    args = parse_args(argv)
    # Console Windows mặc định cp1252 không in được tiếng Việt khi stdout bị chuyển hướng.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if session_factory is None:
        from app.db.session import SessionLocal

        session_factory = SessionLocal

    with session_factory() as session:
        report = plan_refresh(session)
        print(format_report(report))
        if args.apply and report.updates:
            written = apply_refresh(session, report.updates)
            print(f"Đã ghi legal_* cho {written} chunk.")
        elif not args.apply:
            print("Dry-run: chưa ghi DB (thêm --apply để ghi).")
    return 1 if report.skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())

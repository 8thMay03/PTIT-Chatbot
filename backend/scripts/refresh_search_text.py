"""Tính lại ``search_text`` của chunk trong DB mà không chunk lại hay gọi embedding.

Dùng khi chỉ cách ghép ``search_text`` thay đổi (vd. thêm dòng tuần tự hóa hàng
bảng ``Cột: giá trị``): mọi luồng chunk có sẵn (``/documents/{id}/chunk``,
``/datasets/{id}/chunk``, ``/ingest/chunk``) đều embed lại toàn bộ. Script này
chia lại ``parsed_text`` đã lưu bằng đúng ``_chunk_records`` của pipeline, chỉ
cập nhật khi tập id chunk và ``text`` của từng chunk khớp DB (nếu lệch thì bỏ
qua tài liệu đó — cần chunk lại đầy đủ), và chỉ ghi cột ``search_text``; id
chunk, ``text``, metadata và vector giữ nguyên.

Từ chối chạy khi ``EMBEDDING_INPUT_FIELD=search_text`` vì khi đó vector được
tính từ ``search_text`` và sẽ lệch. BM25 tự dựng lại trong tiến trình mới; một
backend đang chạy cần khởi động lại để dựng lại chỉ mục BM25 trong bộ nhớ.

Ví dụ::

    python -m scripts.refresh_search_text            # dry-run: chỉ báo cáo
    python -m scripts.refresh_search_text --apply    # ghi search_text mới
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from statistics import fmean
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, undefer

from app.core.config import settings
from app.db.models import Chunk, Document
from app.ingestion.pipeline import _chunk_records, _ParsedDocument


@dataclass
class DocumentRefresh:
    document_id: str
    title: str
    chunks: int
    changed: int = 0
    skipped_reason: str = ""
    old_lengths: list[int] = field(default_factory=list)
    new_lengths: list[int] = field(default_factory=list)


@dataclass
class RefreshReport:
    documents: list[DocumentRefresh] = field(default_factory=list)
    updates: dict[str, str] = field(default_factory=dict)

    @property
    def changed(self) -> int:
        return sum(item.changed for item in self.documents)

    @property
    def skipped(self) -> list[DocumentRefresh]:
        return [item for item in self.documents if item.skipped_reason]


def plan_refresh(session: Session) -> RefreshReport:
    """Tính ``search_text`` mới cho mọi chunk của tài liệu có ``parsed_text``."""
    report = RefreshReport()
    documents = session.scalars(
        select(Document).options(undefer(Document.parsed_text)).order_by(Document.id)
    ).all()
    for document in documents:
        rows = session.scalars(select(Chunk).where(Chunk.document_id == document.id)).all()
        item = DocumentRefresh(document.id, document.title or "", len(rows))
        report.documents.append(item)
        parsed = _ParsedDocument.from_model(document)
        if parsed.text is None:
            item.skipped_reason = "chưa có parsed_text"
            continue
        records, _ = _chunk_records(parsed.id, parsed.source_path, parsed.title, parsed.text)
        by_id = {row.id: row for row in rows}
        if {record.id for record in records} != set(by_id):
            item.skipped_reason = (
                f"tập chunk id lệch DB ({len(records)} tính lại / {len(rows)} trong DB)"
            )
            continue
        mismatched = [record.id for record in records if by_id[record.id].text != record.text]
        if mismatched:
            item.skipped_reason = f"{len(mismatched)} chunk có text lệch DB (vd. {mismatched[0]})"
            continue
        for record in records:
            old = by_id[record.id].search_text or ""
            item.old_lengths.append(len(old))
            item.new_lengths.append(len(record.search_text))
            if old != record.search_text:
                item.changed += 1
                report.updates[record.id] = record.search_text
    return report


def apply_refresh(session: Session, updates: dict[str, str]) -> int:
    """Ghi ``search_text`` mới, không đụng cột nào khác."""
    for chunk_id, search_text in updates.items():
        session.get(Chunk, chunk_id).search_text = search_text
    session.commit()
    return len(updates)


def format_report(report: RefreshReport) -> str:
    lines: list[str] = []
    for item in report.documents:
        if item.skipped_reason:
            lines.append(f"- {item.document_id} ({item.title}): BỎ QUA — {item.skipped_reason}")
            continue
        old_avg = fmean(item.old_lengths) if item.old_lengths else 0.0
        new_avg = fmean(item.new_lengths) if item.new_lengths else 0.0
        lines.append(
            f"- {item.document_id} ({item.title}): {item.chunks} chunk, {item.changed} đổi "
            f"search_text; độ dài TB {old_avg:.1f} → {new_avg:.1f}, max {max(item.new_lengths, default=0)}"
        )
    lines.append(
        f"Tổng: {len(report.documents)} tài liệu, {report.changed} chunk đổi, "
        f"{len(report.skipped)} tài liệu bỏ qua."
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tính lại search_text của chunk trong DB (không chunk lại, không embedding)."
    )
    parser.add_argument("--apply", action="store_true", help="Ghi vào DB (mặc định chỉ dry-run).")
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None, session_factory: Callable[[], Session] | None = None
) -> int:
    args = parse_args(argv)
    if settings.embedding_input_field.strip().lower() == "search_text":
        print(
            "EMBEDDING_INPUT_FIELD=search_text: vector phụ thuộc search_text, "
            "hãy chunk lại đầy đủ thay vì dùng script này.",
            file=sys.stderr,
        )
        return 2
    if session_factory is None:
        from app.db.session import SessionLocal

        session_factory = SessionLocal

    with session_factory() as session:
        report = plan_refresh(session)
        print(format_report(report))
        if args.apply and report.updates:
            written = apply_refresh(session, report.updates)
            print(f"Đã ghi search_text cho {written} chunk.")
        elif not args.apply:
            print("Dry-run: chưa ghi DB (thêm --apply để ghi).")
    return 1 if report.skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())

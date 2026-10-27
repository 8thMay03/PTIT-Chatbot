"""Background parse jobs.

Parsing a large PDF/DOCX with Docling or LlamaParse can take minutes. The API
validates the request, stages an upload when needed and returns a job
immediately; one worker thread runs the parser so the event loop and the other
endpoints stay responsive. Job state lives in memory: the pipeline still
commits the parsed text and chunks to the database, so a server restart only
loses progress reporting, not stored results.
"""

from __future__ import annotations

import shutil
import threading
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.ingestion.pipeline import IngestionPipeline, ingestion_pipeline
from app.ingestion.uploads import prepare_upload, sanitize_filename

ACTIVE_STATUSES = frozenset({"queued", "running"})


class ParseJobConflict(RuntimeError):
    """A parse job for the same document or uploaded file is already active."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ParseJob:
    id: str
    kind: str
    status: str
    document_id: str | None
    file_name: str | None
    parser_name: str | None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    progress: int = 0
    progress_message: str | None = None


class ParseJobManager:
    """Run at most one heavy parse at a time and expose its current state."""

    def __init__(
        self,
        *,
        pipeline: IngestionPipeline | None = None,
        max_workers: int = 1,
        max_jobs: int = 100,
        staging_root: Path | None = None,
    ) -> None:
        self._pipeline = pipeline or ingestion_pipeline
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ptit-parse")
        self._lock = threading.Lock()
        self._jobs: OrderedDict[str, ParseJob] = OrderedDict()
        # Reserve the key before staging/parsing so two requests cannot overwrite
        # the same source or parse the same document concurrently.
        self._active_keys: dict[str, str] = {}
        self._max_jobs = max_jobs
        self._staging_root = staging_root or settings.database_path / "parse-jobs"

    # ---- Enqueue ----

    def enqueue_parse(
        self,
        document_id: str,
        path: Path,
        *,
        file_name: str | None = None,
        parser_name: str | None = None,
    ) -> ParseJob:
        key = f"document:{document_id}"
        with self._lock:
            job_id = self._reserve_locked(key)
            job = self._add_locked(
                job_id=job_id,
                kind="parse",
                document_id=document_id,
                file_name=file_name or path.name,
                parser_name=parser_name,
            )
        self._executor.submit(self._run_parse, job.id, key, path, document_id, parser_name)
        return job

    def enqueue_upload(
        self,
        filename: str,
        content: bytes,
        *,
        parser_name: str | None = None,
    ) -> ParseJob:
        safe_name = sanitize_filename(filename)
        key = f"upload:{safe_name}"
        with self._lock:
            job_id = self._reserve_locked(key)
            job = self._add_locked(
                job_id=job_id,
                kind="upload",
                document_id=None,
                file_name=safe_name,
                parser_name=parser_name,
            )
            folder = self._staging_root / job.id

        try:
            staged_path = prepare_upload(filename, content, folder)
        except BaseException:
            with self._lock:
                self._jobs.pop(job.id, None)
                self._active_keys.pop(key, None)
            shutil.rmtree(folder, ignore_errors=True)
            raise

        self._executor.submit(self._run_upload, job.id, key, staged_path, parser_name)
        return job

    # ---- Read state ----

    def get(self, job_id: str) -> ParseJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(
        self,
        *,
        document_id: str | None = None,
        active_only: bool = False,
        limit: int = 50,
    ) -> list[ParseJob]:
        with self._lock:
            jobs = [
                job
                for job in self._jobs.values()
                if (document_id is None or job.document_id == document_id)
                and (not active_only or job.status in ACTIVE_STATUSES)
            ]
        return list(reversed(jobs))[:limit]

    def active_for_document(self, document_id: str) -> ParseJob | None:
        with self._lock:
            for job in self._jobs.values():
                if job.document_id == document_id and job.status in ACTIVE_STATUSES:
                    return job
        return None

    # ---- Worker ----

    def _run_parse(
        self,
        job_id: str,
        key: str,
        path: Path,
        document_id: str,
        parser_name: str | None,
    ) -> None:
        self._mark_running(job_id)
        try:
            options = {"parser_name": parser_name} if parser_name is not None else {}
            result = self._pipeline.parse_path(
                path,
                document_id=document_id,
                on_progress=self._progress_callback(job_id),
                **options,
            )
        except Exception as exc:  # noqa: BLE001 - report any parser/DB failure as job error.
            self._finish(job_id, key, status="failed", error=_error_text(exc))
            return
        self._finish(
            job_id,
            key,
            status="succeeded",
            result=result,
            document_id=(result.get("id") if isinstance(result, dict) else None) or document_id,
        )

    def _run_upload(
        self,
        job_id: str,
        key: str,
        staged_path: Path,
        parser_name: str | None,
    ) -> None:
        self._mark_running(job_id)
        result: dict[str, Any] | None = None
        error: str | None = None
        try:
            options = {"parser_name": parser_name} if parser_name is not None else {}
            result = self._pipeline.parse_staged_upload(
                staged_path,
                on_progress=self._progress_callback(job_id),
                **options,
            )
        except Exception as exc:  # noqa: BLE001 - conversion, empty text and DB failures.
            error = _error_text(exc)
        finally:
            shutil.rmtree(staged_path.parent, ignore_errors=True)

        if error is not None:
            self._finish(job_id, key, status="failed", error=error)
        else:
            self._finish(
                job_id,
                key,
                status="succeeded",
                result=result,
                document_id=(result.get("id") if isinstance(result, dict) else None),
            )

    def _progress_callback(self, job_id: str):
        def report(percent: int, message: str) -> None:
            self._update_progress(job_id, percent, message)

        return report

    # ---- Internal state ----

    def _reserve_locked(self, key: str) -> str:
        active_id = self._active_keys.get(key)
        if active_id:
            active = self._jobs.get(active_id)
            label = active.file_name if active and active.file_name else "tài liệu này"
            raise ParseJobConflict(f"“{label}” đang được parse; hãy chờ job hiện tại xong.")
        job_id = uuid.uuid4().hex
        self._active_keys[key] = job_id
        return job_id

    def _add_locked(
        self,
        *,
        job_id: str,
        kind: str,
        document_id: str | None,
        file_name: str | None,
        parser_name: str | None,
    ) -> ParseJob:
        job = ParseJob(
            id=job_id,
            kind=kind,
            status="queued",
            document_id=document_id,
            file_name=file_name,
            parser_name=parser_name,
            created_at=_now(),
            progress=0,
            progress_message="Đang chờ trong hàng đợi",
        )
        self._jobs[job_id] = job
        return job

    def _mark_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                self._jobs[job_id] = replace(
                    job,
                    status="running",
                    started_at=_now(),
                    progress=max(job.progress, 2),
                    progress_message="Đang khởi động parser",
                )

    def _update_progress(self, job_id: str, percent: int, message: str) -> None:
        bounded = max(0, min(99, int(percent)))
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status not in ACTIVE_STATUSES:
                return
            self._jobs[job_id] = replace(
                job,
                progress=max(job.progress, bounded),
                progress_message=message or job.progress_message,
            )

    def _finish(
        self,
        job_id: str,
        key: str,
        *,
        status: str,
        error: str | None = None,
        result: dict[str, Any] | None = None,
        document_id: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                succeeded = status == "succeeded"
                self._jobs[job_id] = replace(
                    job,
                    status=status,
                    finished_at=_now(),
                    error=error,
                    result=result,
                    document_id=document_id or job.document_id,
                    progress=100 if succeeded else job.progress,
                    progress_message="Hoàn tất" if succeeded else "Parse thất bại",
                )
            self._active_keys.pop(key, None)
            self._prune_locked()

    def _prune_locked(self) -> None:
        if len(self._jobs) <= self._max_jobs:
            return
        for job_id in list(self._jobs):
            if len(self._jobs) <= self._max_jobs:
                break
            if self._jobs[job_id].status not in ACTIVE_STATUSES:
                del self._jobs[job_id]


def _error_text(exc: Exception) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


parse_jobs = ParseJobManager()

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from app.ingestion.jobs import ParseJobConflict, ParseJobManager
from app.ingestion.uploads import DocumentUploadError
from app.parsers import DocumentParseError


def _item(*, document_id: str = "doc-1", file_name: str = "a.md", status: str = "parsed") -> dict:
    return {
        "id": document_id,
        "title": Path(file_name).stem,
        "file_name": file_name,
        "source_path": f"data/{file_name}",
        "file_type": Path(file_name).suffix.lstrip("."),
        "status": status,
        "chunk_count": 0,
        "parsed_at": None,
        "markdown_edited": False,
        "size_bytes": 10,
        "created_at": None,
        "updated_at": None,
    }


class FakePipeline:
    def __init__(self, *, parse=None, upload=None) -> None:
        self._parse = parse
        self._upload = upload
        self.parse_calls: list[tuple] = []
        self.upload_calls: list[tuple] = []

    def parse_path(self, path, *, document_id=None, parser_name=None, on_progress=None):
        self.parse_calls.append((path, document_id, parser_name))
        if self._parse is not None:
            return self._parse(
                path,
                document_id=document_id,
                parser_name=parser_name,
                on_progress=on_progress,
            )
        return _item(document_id=document_id or "doc-1", file_name=Path(path).name)

    def parse_staged_upload(self, staged_path, *, parser_name=None, on_progress=None):
        self.upload_calls.append((staged_path, parser_name))
        if self._upload is not None:
            return self._upload(
                staged_path,
                parser_name=parser_name,
                on_progress=on_progress,
            )
        return _item(document_id="doc-upload", file_name=staged_path.name)


def _wait_for(manager: ParseJobManager, job_id: str, statuses: set[str], timeout: float = 3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = manager.get(job_id)
        if job is not None and job.status in statuses:
            return job
        time.sleep(0.01)
    raise AssertionError(f"job {job_id} did not reach {statuses}; last={manager.get(job_id)}")


def test_enqueue_parse_returns_before_parser_finishes(tmp_path: Path) -> None:
    started = threading.Event()
    release = threading.Event()

    def parse(path, *, document_id=None, parser_name=None, on_progress=None):
        started.set()
        assert release.wait(3)
        return _item(document_id=document_id, file_name=Path(path).name)

    manager = ParseJobManager(
        pipeline=FakePipeline(parse=parse),
        staging_root=tmp_path / "staging",
    )

    job = manager.enqueue_parse("doc-1", tmp_path / "a.md", file_name="a.md")

    assert job.status == "queued"
    assert started.wait(2)
    assert manager.get(job.id).status == "running"

    release.set()
    done = _wait_for(manager, job.id, {"succeeded"})
    assert done.result["id"] == "doc-1"
    assert done.started_at is not None
    assert done.finished_at is not None


def test_failed_parse_records_error(tmp_path: Path) -> None:
    def parse(path, *, document_id=None, parser_name=None, on_progress=None):
        raise DocumentParseError("conversion unavailable")

    manager = ParseJobManager(
        pipeline=FakePipeline(parse=parse),
        staging_root=tmp_path / "staging",
    )

    job = manager.enqueue_parse("doc-1", tmp_path / "broken.pdf", file_name="broken.pdf")

    done = _wait_for(manager, job.id, {"failed"})
    assert done.error == "conversion unavailable"
    assert done.result is None


def test_progress_is_reported_and_finishes_at_100(tmp_path: Path) -> None:
    reported = threading.Event()
    release = threading.Event()

    def parse(path, *, document_id=None, parser_name=None, on_progress=None):
        on_progress(35, "Đang parse 5/14 trang")
        reported.set()
        assert release.wait(3)
        on_progress(97, "Đang lưu kết quả parse")
        return _item(document_id=document_id, file_name=Path(path).name)

    manager = ParseJobManager(
        pipeline=FakePipeline(parse=parse),
        staging_root=tmp_path / "staging",
    )

    job = manager.enqueue_parse("doc-1", tmp_path / "a.pdf", file_name="a.pdf")
    assert reported.wait(2)
    running = manager.get(job.id)
    assert running.progress == 35
    assert running.progress_message == "Đang parse 5/14 trang"

    release.set()
    done = _wait_for(manager, job.id, {"succeeded"})
    assert done.progress == 100
    assert done.progress_message == "Hoàn tất"


def test_duplicate_active_parse_is_rejected_then_allowed_after_finish(tmp_path: Path) -> None:
    release = threading.Event()

    def parse(path, *, document_id=None, parser_name=None, on_progress=None):
        assert release.wait(3)
        return _item(document_id=document_id, file_name=Path(path).name)

    manager = ParseJobManager(
        pipeline=FakePipeline(parse=parse),
        staging_root=tmp_path / "staging",
    )

    first = manager.enqueue_parse("doc-1", tmp_path / "a.md", file_name="a.md")
    with pytest.raises(ParseJobConflict):
        manager.enqueue_parse("doc-1", tmp_path / "a.md", file_name="a.md")

    release.set()
    _wait_for(manager, first.id, {"succeeded"})

    second = manager.enqueue_parse("doc-1", tmp_path / "a.md", file_name="a.md")
    assert second.id != first.id
    _wait_for(manager, second.id, {"succeeded"})


def test_upload_is_staged_then_cleaned_after_success(tmp_path: Path) -> None:
    captured: dict = {}

    def upload(staged_path, *, parser_name=None, on_progress=None):
        captured["path"] = staged_path
        captured["content"] = staged_path.read_bytes()
        captured["parser_name"] = parser_name
        return _item(document_id="doc-upload", file_name=staged_path.name)

    manager = ParseJobManager(
        pipeline=FakePipeline(upload=upload),
        staging_root=tmp_path / "staging",
    )

    job = manager.enqueue_upload("policy.md", b"# Policy", parser_name="text")

    assert job.kind == "upload"
    assert job.status == "queued"
    assert job.document_id is None

    done = _wait_for(manager, job.id, {"succeeded"})
    assert done.result["id"] == "doc-upload"
    assert done.document_id == "doc-upload"
    assert captured["content"] == b"# Policy"
    assert captured["parser_name"] == "text"
    assert not captured["path"].parent.exists()


def test_invalid_upload_releases_reservation(tmp_path: Path) -> None:
    manager = ParseJobManager(
        pipeline=FakePipeline(),
        staging_root=tmp_path / "staging",
    )

    with pytest.raises(DocumentUploadError):
        manager.enqueue_upload("notes.exe", b"not supported")
    # The reservation is gone: a retry reports the same validation error instead
    # of a misleading "already parsing" conflict.
    with pytest.raises(DocumentUploadError):
        manager.enqueue_upload("notes.exe", b"not supported")

    assert manager.list() == []


def test_list_filters_newest_first_and_active_only(tmp_path: Path) -> None:
    release = threading.Event()

    def parse(path, *, document_id=None, parser_name=None, on_progress=None):
        assert release.wait(3)
        return _item(document_id=document_id, file_name=Path(path).name)

    manager = ParseJobManager(
        pipeline=FakePipeline(parse=parse),
        staging_root=tmp_path / "staging",
    )

    first = manager.enqueue_parse("doc-1", tmp_path / "a.md", file_name="a.md")
    _wait_for(manager, first.id, {"running"})
    second = manager.enqueue_parse("doc-2", tmp_path / "b.md", file_name="b.md")

    active = manager.list(active_only=True)
    assert [job.id for job in active] == [second.id, first.id]
    assert manager.list(document_id="doc-2") == [second]

    release.set()
    _wait_for(manager, first.id, {"succeeded"})
    _wait_for(manager, second.id, {"succeeded"})
    assert manager.list(active_only=True) == []

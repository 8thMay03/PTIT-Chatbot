from pathlib import Path

import pytest

from app.ingestion.uploads import (
    DocumentUploadError,
    prepare_upload,
    sanitize_filename,
)


def test_sanitize_filename_strips_directories_and_unsafe_characters() -> None:
    assert sanitize_filename("../etc/passwd.md") == "passwd.md"
    assert sanitize_filename("quy che?.txt") == "quy che_.txt"


def test_prepare_upload_writes_utf8_file(tmp_path: Path) -> None:
    path = prepare_upload("so-tay.md", "# Điều kiện tốt nghiệp\n".encode("utf-8"), tmp_path)

    assert path == tmp_path / "so-tay.md"
    assert path.read_text(encoding="utf-8") == "# Điều kiện tốt nghiệp\n"


def test_prepare_upload_rejects_unsupported_extension(tmp_path: Path) -> None:
    with pytest.raises(DocumentUploadError, match="Chỉ hỗ trợ"):
        prepare_upload("legacy.doc", b"\xd0\xcf\x11\xe0", tmp_path)


def test_prepare_upload_writes_binary_pdf_and_docx(tmp_path: Path) -> None:
    pdf = prepare_upload("so-tay.pdf", b"%PDF-1.7 binary\xff", tmp_path)
    docx = prepare_upload("huong-dan.docx", b"PK\x03\x04 zip\xff", tmp_path)

    assert pdf.read_bytes() == b"%PDF-1.7 binary\xff"
    assert docx.read_bytes() == b"PK\x03\x04 zip\xff"


def test_prepare_upload_rejects_mismatched_binary_signature(tmp_path: Path) -> None:
    with pytest.raises(DocumentUploadError, match="không hợp lệ"):
        prepare_upload("fake.pdf", b"# just markdown", tmp_path)
    assert not (tmp_path / "fake.pdf").exists()


def test_prepare_upload_rejects_empty_file(tmp_path: Path) -> None:
    with pytest.raises(DocumentUploadError, match="trống"):
        prepare_upload("empty.md", b"", tmp_path)


def test_prepare_upload_rejects_non_utf8(tmp_path: Path) -> None:
    with pytest.raises(DocumentUploadError, match="UTF-8"):
        prepare_upload("bad.md", b"\xff\xfe", tmp_path)

import logging
import sys
from pathlib import Path

import pytest

from app.core.config import settings
from app.ingestion import converters
from app.ingestion.converters import DocumentConversionError, read_document_text
from app.ingestion.loaders import load_documents


class _FakeDocument:
    def __init__(self, markdown: str) -> None:
        self.markdown = markdown

    def export_to_markdown(self, image_placeholder: str = "<!-- image -->") -> str:
        return self.markdown


class _FakeConverter:
    def __init__(self, markdown: str) -> None:
        self.markdown = markdown
        self.calls: list[Path] = []

    def convert(self, path: Path):
        self.calls.append(path)
        return type("Result", (), {"document": _FakeDocument(self.markdown)})()


@pytest.fixture
def fake_converter(monkeypatch, tmp_path: Path) -> _FakeConverter:
    # Decomposed "Điều" (NFD) as emitted by some PDF text layers.
    converter = _FakeConverter("# \u0110ie\u0302\u0300u 1\n\nCT&amp;CTSV\n\n<!-- image -->\n\n\n\n| A | B |\n|---|---|\n| 1 | 2 |")
    monkeypatch.setattr(converters, "_get_converter", lambda: converter)
    monkeypatch.setattr(settings, "converted_documents_path", tmp_path / "converted")
    return converter


def test_text_files_are_read_directly(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    path.write_text("# Học phí\n", encoding="utf-8")

    assert read_document_text(path) == "# Học phí\n"


def test_pdf_is_converted_normalized_and_cached(fake_converter, tmp_path: Path) -> None:
    path = tmp_path / "so-tay.pdf"
    path.write_bytes(b"%PDF-1.7 fake")

    first = read_document_text(path)
    second = read_document_text(path)

    assert first == "# Điều 1\n\nCT&CTSV\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
    assert second == first
    assert len(fake_converter.calls) == 1


def test_read_without_convert_only_uses_cache(fake_converter, tmp_path: Path) -> None:
    path = tmp_path / "huong-dan.docx"
    path.write_bytes(b"PK\x03\x04 fake")

    assert read_document_text(path, convert=False) is None
    assert fake_converter.calls == []

    read_document_text(path)
    assert read_document_text(path, convert=False) is not None


def test_changed_file_is_reconverted(fake_converter, tmp_path: Path) -> None:
    path = tmp_path / "so-tay.pdf"
    path.write_bytes(b"%PDF v1")
    read_document_text(path)
    path.write_bytes(b"%PDF v2")
    read_document_text(path)

    assert len(fake_converter.calls) == 2


def test_table_cell_padding_is_compacted(monkeypatch, tmp_path: Path) -> None:
    markdown = (
        "| TT   | Thang điểm 10      |\n"
        "|------|--------------------|\n"
        "| a) Loại đạt   | a) Loại đạt   |\n"
        "| 1    | 8,5 - 10           |\n"
    )
    monkeypatch.setattr(converters, "_get_converter", lambda: _FakeConverter(markdown))
    monkeypatch.setattr(settings, "converted_documents_path", tmp_path / "converted")
    path = tmp_path / "bang-diem.pdf"
    path.write_bytes(b"%PDF table")

    assert read_document_text(path) == (
        "| TT | Thang điểm 10 |\n|---|---|\n| a) Loại đạt | |\n| 1 | 8,5 - 10 |\n"
    )


def test_bold_only_lines_become_headings(monkeypatch, tmp_path: Path) -> None:
    markdown = (
        "**HƯỚNG DẪN MUA BẢO HIỂM Y TẾ**\n\n"
        "**1. Khai báo thông tin BHYT:**\n\n"
        "Sinh viên điền mục **BHYT** .\n\n"
        "**2. Hoàn tiền** (đối với sinh viên đã có thẻ)\n"
    )
    monkeypatch.setattr(converters, "_get_converter", lambda: _FakeConverter(markdown))
    monkeypatch.setattr(settings, "converted_documents_path", tmp_path / "converted")
    path = tmp_path / "bhyt.docx"
    path.write_bytes(b"PK\x03\x04 bhyt")

    text = read_document_text(path)

    assert text.splitlines()[0] == "# HƯỚNG DẪN MUA BẢO HIỂM Y TẾ"
    assert "## 1. Khai báo thông tin BHYT" in text
    assert "Sinh viên điền mục **BHYT** ." in text
    assert "**2. Hoàn tiền** (đối với sinh viên đã có thẻ)" in text


def test_empty_conversion_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(converters, "_get_converter", lambda: _FakeConverter("<!-- image -->"))
    monkeypatch.setattr(settings, "converted_documents_path", tmp_path / "converted")
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF scan")

    with pytest.raises(DocumentConversionError, match="OCR"):
        read_document_text(path)


class _FakeTorch:
    __version__ = "2.0.0+cpu"

    def __init__(self, cuda: bool) -> None:
        self.cuda = type("Cuda", (), {"is_available": staticmethod(lambda: cuda)})()


@pytest.mark.parametrize(
    ("device", "has_cuda", "expected"),
    [("auto", True, True), ("auto", False, False), ("cuda:0", True, True), ("cpu", True, False)],
)
def test_resolve_cuda(monkeypatch, device: str, has_cuda: bool, expected: bool) -> None:
    monkeypatch.setitem(sys.modules, "torch", _FakeTorch(has_cuda))

    assert converters._resolve_cuda(device) is expected


def test_resolve_cuda_warns_when_gpu_requested_but_torch_is_cpu_only(monkeypatch, caplog) -> None:
    monkeypatch.setitem(sys.modules, "torch", _FakeTorch(False))

    with caplog.at_level(logging.WARNING, logger=converters.__name__):
        assert converters._resolve_cuda("cuda") is False

    assert "CUDA" in caplog.text


def test_load_documents_skips_files_that_fail_conversion(monkeypatch, tmp_path: Path) -> None:
    def broken_converter():
        raise DocumentConversionError("boom")

    monkeypatch.setattr(converters, "_get_converter", broken_converter)
    monkeypatch.setattr(settings, "converted_documents_path", tmp_path / "converted")
    data = tmp_path / "data"
    data.mkdir()
    (data / "ok.md").write_text("# OK\n", encoding="utf-8")
    (data / "broken.pdf").write_bytes(b"%PDF broken")
    (data / "legacy.doc").write_bytes(b"ignored")

    documents = load_documents(data)

    assert [document.path.name for document in documents] == ["ok.md"]

import logging
import sys
from pathlib import Path

import pytest

from app.core.config import settings
from app.parsers import DocumentParseError, docling, read_document_text
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
    monkeypatch.setattr(docling, "_get_converter", lambda: converter)
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


def test_pre_extraction_docling_cache_is_read_without_conversion(fake_converter, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "docling_ocr_enabled", False)
    source = tmp_path / "legacy.pdf"
    source.write_bytes(b"%PDF-1.7 legacy")
    # Existing docling-v2/no-ocr cache filename produced before package extraction.
    cache = settings.converted_documents_path / "03ac7ad915a49a86bfdef44e4408d17efca6fb67432052aa1e38fafb04da24c1.md"
    cache.parent.mkdir(parents=True)
    cache.write_text("# Existing export\n\n| A | B |\n|---|---|\n| 100 | 100 |", encoding="utf-8")

    assert "| 100 | 100 |" in read_document_text(source, convert=False)
    assert fake_converter.calls == []


def test_table_cell_padding_is_compacted(monkeypatch, tmp_path: Path) -> None:
    markdown = (
        "| TT   | Thang điểm 10      |\n"
        "|------|--------------------|\n"
        "| a) Loại đạt   | a) Loại đạt   |\n"
        "| 1    | 8,5 - 10           |\n"
    )
    monkeypatch.setattr(docling, "_get_converter", lambda: _FakeConverter(markdown))
    monkeypatch.setattr(settings, "converted_documents_path", tmp_path / "converted")
    path = tmp_path / "bang-diem.pdf"
    path.write_bytes(b"%PDF table")

    assert read_document_text(path) == (
        "| TT | Thang điểm 10 |\n|---|---|\n| a) Loại đạt | a) Loại đạt |\n| 1 | 8,5 - 10 |\n"
    )


def test_bold_only_lines_become_headings(monkeypatch, tmp_path: Path) -> None:
    markdown = (
        "**HƯỚNG DẪN MUA BẢO HIỂM Y TẾ**\n\n"
        "**1. Khai báo thông tin BHYT:**\n\n"
        "Sinh viên điền mục **BHYT** .\n\n"
        "**2. Hoàn tiền** (đối với sinh viên đã có thẻ)\n"
    )
    monkeypatch.setattr(docling, "_get_converter", lambda: _FakeConverter(markdown))
    monkeypatch.setattr(settings, "converted_documents_path", tmp_path / "converted")
    path = tmp_path / "bhyt.docx"
    path.write_bytes(b"PK\x03\x04 bhyt")

    text = read_document_text(path)

    assert text.splitlines()[0] == "# HƯỚNG DẪN MUA BẢO HIỂM Y TẾ"
    assert "## 1. Khai báo thông tin BHYT" in text
    assert "Sinh viên điền mục **BHYT** ." in text
    assert "**2. Hoàn tiền** (đối với sinh viên đã có thẻ)" in text


def test_empty_conversion_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(docling, "_get_converter", lambda: _FakeConverter("<!-- image -->"))
    monkeypatch.setattr(settings, "converted_documents_path", tmp_path / "converted")
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF scan")

    with pytest.raises(DocumentParseError, match="OCR"):
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

    assert docling._resolve_cuda(device) is expected


def test_resolve_cuda_warns_when_gpu_requested_but_torch_is_cpu_only(monkeypatch, caplog) -> None:
    monkeypatch.setitem(sys.modules, "torch", _FakeTorch(False))
    # Migration logging setup in other tests may disable pre-existing loggers.
    monkeypatch.setattr(docling.logger, "disabled", False)

    with caplog.at_level(logging.WARNING, logger=docling.__name__):
        assert docling._resolve_cuda("cuda") is False

    assert "CUDA" in caplog.text


def test_load_documents_rejects_files_that_fail_conversion(monkeypatch, tmp_path: Path) -> None:
    def broken_converter():
        raise DocumentParseError("boom")

    monkeypatch.setattr(docling, "_get_converter", broken_converter)
    monkeypatch.setattr(settings, "converted_documents_path", tmp_path / "converted")
    data = tmp_path / "data"
    data.mkdir()
    (data / "ok.md").write_text("# OK\n", encoding="utf-8")
    (data / "broken.pdf").write_bytes(b"%PDF broken")
    (data / "legacy.doc").write_bytes(b"ignored")

    with pytest.raises(DocumentParseError, match="broken.pdf"):
        load_documents(data)


@pytest.mark.parametrize("value", ["100", "0", "a) Loại đạt"])
def test_equal_table_cells_are_preserved_including_cached_exports(fake_converter, tmp_path, value):
    path = tmp_path / "table.pdf"
    path.write_bytes(b"%PDF equal cells")
    fake_converter.markdown = f"| Year A | Year B |\n|---|---|\n| {value} | {value} |"

    first = read_document_text(path)
    cached = read_document_text(path, convert=False)

    assert f"| {value} | {value} |" in first
    assert cached == first
    assert len(fake_converter.calls) == 1


def test_load_documents_rejects_empty_supported_file(tmp_path):
    (tmp_path / "empty.md").write_text("  \n", encoding="utf-8")

    with pytest.raises(DocumentParseError, match="empty.md"):
        load_documents(tmp_path)


def test_load_documents_ignores_unsupported_files(tmp_path):
    (tmp_path / "ok.md").write_text("# OK\n", encoding="utf-8")
    (tmp_path / "legacy.doc").write_bytes(b"ignored")

    assert [document.path.name for document in load_documents(tmp_path)] == ["ok.md"]

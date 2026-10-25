import logging
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.parsers as parsers
from app.core.config import settings
from app.parsers import DocumentParseError, build_registry, docling, llamaparse, read_document_text
from app.parsers.llamaparse import LlamaParseParser

API_KEY = "llx-test-key-not-real"


class _StatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code} body with secrets")
        self.status_code = status_code


def _page(number: int, markdown: str | None = None, *, success: bool = True):
    return SimpleNamespace(page_number=number, markdown=markdown, success=success, error=None if success else "x")


def _result(*pages, credits: float = 6.0):
    return SimpleNamespace(
        markdown=SimpleNamespace(pages=list(pages)),
        job=SimpleNamespace(usage=SimpleNamespace(credits=credits)),
    )


class FakeSDK:
    """Stand-in for the llama_cloud package so tests need neither the SDK nor network."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.clients: list[dict] = []
        self.outcome: object = _result(_page(2, "Nội dung trang 2"), _page(1, "# Điều 1\n\n![logo](img.png)\n\n\n\nTrang 1"))
        self.module = types.ModuleType("llama_cloud")
        for name in ("PollingTimeoutError", "PollingError", "APIConnectionError"):
            setattr(self.module, name, type(name, (Exception,), {}))
        self.module.APIStatusError = _StatusError
        sdk = self

        class LlamaCloud:
            def __init__(self, **kwargs) -> None:
                sdk.clients.append(kwargs)
                self.parsing = self

            def __enter__(self):
                return self

            def __exit__(self, *exc) -> None:
                return None

            def parse(self, **kwargs):
                upload_name, handle = kwargs["upload_file"]
                sdk.calls.append({**kwargs, "upload_file": (upload_name, handle.read())})
                if isinstance(sdk.outcome, BaseException):
                    raise sdk.outcome
                return sdk.outcome

        self.module.LlamaCloud = LlamaCloud


@pytest.fixture
def sdk(monkeypatch, tmp_path: Path) -> FakeSDK:
    fake = FakeSDK()
    monkeypatch.setitem(sys.modules, "llama_cloud", fake.module)
    monkeypatch.setattr(settings, "converted_documents_path", tmp_path / "converted")
    monkeypatch.setattr(settings, "llamaparse_enabled", True)
    monkeypatch.setattr(settings, "llama_cloud_api_key", API_KEY)
    monkeypatch.setattr(settings, "llamaparse_tier", "cost_effective")
    monkeypatch.setattr(settings, "llamaparse_version", "latest")
    monkeypatch.setattr(settings, "llamaparse_language", "vi")
    monkeypatch.setattr(parsers, "registry", build_registry())
    return fake


@pytest.fixture
def pdf(tmp_path: Path) -> Path:
    path = tmp_path / "so-tay.pdf"
    path.write_bytes(b"%PDF-1.7 fake")
    return path


def test_parse_sends_options_and_joins_pages_in_order(sdk: FakeSDK, pdf: Path) -> None:
    text = read_document_text(pdf, parser_name="llamaparse")

    assert text == "# Điều 1\n\nTrang 1\n\nNội dung trang 2\n"
    (call,) = sdk.calls
    assert call["upload_file"] == ("so-tay.pdf", b"%PDF-1.7 fake")
    assert call["tier"] == "cost_effective" and call["version"] == "latest"
    assert call["expand"] == ["markdown"]
    assert call["processing_options"] == {"ocr_parameters": {"languages": ["vi"]}}
    assert call["output_options"]["markdown"]["tables"]["output_tables_as_markdown"] is True
    assert sdk.clients[0]["api_key"] == API_KEY
    assert sdk.clients[0]["timeout"] == call["timeout"] == settings.llamaparse_timeout_seconds


def test_second_parse_and_preview_read_cache_without_api(sdk: FakeSDK, pdf: Path) -> None:
    assert read_document_text(pdf, parser_name="llamaparse", convert=False) is None
    assert sdk.calls == []

    first = read_document_text(pdf, parser_name="llamaparse")
    assert read_document_text(pdf, parser_name="llamaparse") == first
    assert read_document_text(pdf, parser_name="llamaparse", convert=False) == first
    assert len(sdk.calls) == 1


def test_cache_is_separate_from_docling_and_keyed_by_options(sdk: FakeSDK, pdf: Path, monkeypatch) -> None:
    read_document_text(pdf, parser_name="llamaparse")
    cache_file = llamaparse._cache_path(pdf)

    assert cache_file.parent == settings.converted_documents_path / "llamaparse"
    assert cache_file != docling._cache_path(pdf)
    assert API_KEY not in cache_file.read_text(encoding="utf-8")

    monkeypatch.setattr(settings, "llamaparse_tier", "agentic")
    assert read_document_text(pdf, parser_name="llamaparse", convert=False) is None
    monkeypatch.setattr(settings, "llamaparse_tier", "cost_effective")
    monkeypatch.setattr(settings, "llamaparse_language", "en")
    assert read_document_text(pdf, parser_name="llamaparse", convert=False) is None


def test_changed_file_is_parsed_again(sdk: FakeSDK, pdf: Path) -> None:
    read_document_text(pdf, parser_name="llamaparse")
    pdf.write_bytes(b"%PDF-1.7 changed")
    read_document_text(pdf, parser_name="llamaparse")

    assert len(sdk.calls) == 2


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (lambda m: m.PollingTimeoutError("slow"), "quá thời gian chờ"),
        (lambda m: m.PollingError("Job x failed with status: FAILED"), "không parse được"),
        (lambda m: m.APIConnectionError("down"), "Không kết nối được LlamaCloud"),
        (lambda m: m.APIStatusError(401), "không hợp lệ"),
        (lambda m: m.APIStatusError(402), "hết credit"),
        (lambda m: m.APIStatusError(429), "giới hạn tần suất"),
        (lambda m: m.APIStatusError(500), "HTTP 500"),
    ],
)
def test_sdk_errors_become_parse_errors_without_response_body(sdk: FakeSDK, pdf: Path, error, message) -> None:
    sdk.outcome = error(sdk.module)

    with pytest.raises(DocumentParseError, match=message) as raised:
        read_document_text(pdf, parser_name="llamaparse")

    assert "secrets" not in str(raised.value)
    assert not llamaparse._cache_path(pdf).exists()


def test_empty_result_is_rejected_and_not_cached(sdk: FakeSDK, pdf: Path) -> None:
    sdk.outcome = _result(_page(1, "  ![chart](c.png)  "))

    with pytest.raises(DocumentParseError, match="không trích được nội dung"):
        read_document_text(pdf, parser_name="llamaparse")
    assert not llamaparse._cache_path(pdf).exists()


def test_failed_pages_are_skipped_but_all_failed_is_an_error(sdk: FakeSDK, pdf: Path, caplog, monkeypatch) -> None:
    sdk.outcome = _result(_page(1, "Trang 1"), _page(2, success=False))
    # Alembic's fileConfig (test_database_postgres) disables loggers created before it.
    monkeypatch.setattr(llamaparse.logger, "disabled", False)
    with caplog.at_level(logging.WARNING, logger=llamaparse.__name__):
        assert read_document_text(pdf, parser_name="llamaparse") == "Trang 1\n"
    assert "bỏ qua 1 trang lỗi" in caplog.text

    pdf.write_bytes(b"%PDF other")
    sdk.outcome = _result(_page(1, success=False))
    with pytest.raises(DocumentParseError, match="không parse được trang nào"):
        read_document_text(pdf, parser_name="llamaparse")


def test_missing_sdk_has_install_hint(sdk: FakeSDK, pdf: Path, monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "llama_cloud", None)

    with pytest.raises(DocumentParseError, match=r"pip install -e \"\.\[llamaparse\]\""):
        read_document_text(pdf, parser_name="llamaparse")


def test_unconfigured_parser_refuses_to_call_api(sdk: FakeSDK, pdf: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "llama_cloud_api_key", "  ")

    with pytest.raises(DocumentParseError, match="chưa được cấu hình"):
        LlamaParseParser().parse(pdf)
    assert sdk.calls == []

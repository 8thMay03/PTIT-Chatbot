import logging
from pathlib import Path

import pytest

import app.parsers as parsers
from app.core.config import settings
from app.ingestion.loaders import load_documents
from app.ingestion.uploads import prepare_upload
from app.parsers import (
    DocumentParseError,
    build_registry,
    read_document_text,
    resolve_parser_name,
)
from app.parsers.registry import ParserRegistry
from app.parsers.text import TextParser


class StubParser:
    def __init__(self, name="custom", extensions=frozenset({".custom"})):
        self.name = name
        self.extensions = extensions
        self.calls = []

    def parse(self, path, *, convert=True):
        self.calls.append((path, convert))
        return f"# Parsed by {self.name}\n" if convert else None


def test_registry_routes_case_insensitive_extensions():
    text = TextParser()
    custom = StubParser()
    registry = ParserRegistry([text, custom])

    assert registry.get_parser(Path("note.MD")) is text
    assert registry.get_parser(Path("source.CUSTOM")) is custom
    assert registry.supported_extensions == {".md", ".txt", ".custom"}


def test_registry_supports_named_alternatives_and_explicit_default():
    first = StubParser("first", frozenset({".pdf"}))
    alternative = StubParser("alternative", frozenset({".pdf"}))
    registry = ParserRegistry([first, alternative])
    source = Path("policy.pdf")

    assert registry.get_parser(source) is first
    assert registry.get_parser(source, parser_name="alternative") is alternative
    preferred = StubParser("preferred", frozenset({".pdf"}))
    registry.register(preferred, default=True)
    assert registry.get_parser(source) is preferred
    assert registry.get_parser(source, parser_name="first") is first
    assert registry.list_parsers(Path("policy.PDF")) == [
        {"name": "first", "is_default": False},
        {"name": "alternative", "is_default": False},
        {"name": "preferred", "is_default": True},
    ]
    assert registry.list_parsers(Path("file.doc")) == []


@pytest.mark.parametrize(
    ("path", "parser_name", "message"),
    [("file.doc", None, ".doc"), ("file", None, "không có"),
     ("file.md", "missing", "missing"), ("file.pdf", "text", "text")],
)
def test_registry_rejects_unsupported_input(path, parser_name, message):
    registry = ParserRegistry([TextParser()])

    with pytest.raises(DocumentParseError, match=message):
        registry.get_parser(Path(path), parser_name=parser_name)


def test_registry_rejects_duplicate_names_without_changing_default():
    original = StubParser()
    registry = ParserRegistry([original])

    with pytest.raises(ValueError, match="custom"):
        registry.register(StubParser(), default=True)

    assert registry.get_parser(Path("file.custom")) is original


def test_facade_forwards_parser_choice_and_preview_flag(monkeypatch):
    first = StubParser("first")
    alternative = StubParser("alternative")
    monkeypatch.setattr(parsers, "registry", ParserRegistry([first, alternative]))
    source = Path("file.custom")

    assert read_document_text(source, parser_name="alternative") == "# Parsed by alternative\n"
    assert read_document_text(source, convert=False) is None
    assert alternative.calls == [(source, True)]
    assert first.calls == [(source, False)]


def test_facade_reports_progress_and_keeps_legacy_parsers_working(monkeypatch):
    class ProgressParser(StubParser):
        def parse(self, path, *, convert=True, on_progress=None):
            if on_progress is not None:
                on_progress(40, "Đang đọc thử")
            return "# Tiến trình\n"

    progress_parser = ProgressParser("progress")
    legacy_parser = StubParser("legacy")
    monkeypatch.setattr(
        parsers,
        "registry",
        ParserRegistry([progress_parser]),
    )
    source = Path("file.custom")
    events = []

    assert (
        read_document_text(
            source, on_progress=lambda percent, message: events.append((percent, message))
        )
        == "# Tiến trình\n"
    )
    assert (40, "Đang đọc thử") in events
    assert events[-1] == (92, "Đang chuẩn hóa Markdown")

    events.clear()
    monkeypatch.setattr(parsers, "registry", ParserRegistry([legacy_parser]))
    assert (
        read_document_text(
            source, on_progress=lambda percent, message: events.append((percent, message))
        )
        == "# Parsed by legacy\n"
    )
    assert events == [(8, "Đang đọc tài liệu"), (92, "Đang chuẩn hóa Markdown")]


def test_new_binary_format_is_discovered_by_uploads_and_loaders(monkeypatch, tmp_path):
    custom = StubParser()
    registry = ParserRegistry([TextParser()])
    monkeypatch.setattr(parsers, "registry", registry)
    registry.register(custom)
    content = b"\xff\xfe custom binary data"

    source = prepare_upload("file.custom", content, tmp_path)
    documents = load_documents(tmp_path)

    assert source.read_bytes() == content
    assert len(documents) == 1
    assert documents[0].path == source
    assert documents[0].text == "# Parsed by custom\n"
    assert custom.calls == [(source, True)]


def test_legacy_converter_public_imports_remain_compatible(tmp_path):
    from app.ingestion import converters
    from app.parsers import docling

    source = tmp_path / "note.txt"
    source.write_text("Legacy caller", encoding="utf-8")

    assert converters.DocumentConversionError is DocumentParseError
    assert converters.read_document_text(source) == "Legacy caller"
    assert converters.convert_with_docling is docling.convert_with_docling
    assert converters.SUPPORTED_EXTENSIONS == {".md", ".txt", ".pdf", ".docx"}


@pytest.mark.parametrize(
    ("enabled", "api_key", "expected"),
    [
        (True, "llx-key", [{"name": "docling", "is_default": True}, {"name": "llamaparse", "is_default": False}]),
        (False, "llx-key", [{"name": "docling", "is_default": True}]),
        (True, None, [{"name": "docling", "is_default": True}]),
        (True, "   ", [{"name": "docling", "is_default": True}]),
    ],
)
def test_llamaparse_is_an_opt_in_alternative_to_docling(monkeypatch, enabled, api_key, expected):
    monkeypatch.setattr(settings, "llamaparse_enabled", enabled)
    monkeypatch.setattr(settings, "llama_cloud_api_key", api_key)
    registry = build_registry()

    for name in ("policy.pdf", "huong-dan.DOCX"):
        assert registry.list_parsers(Path(name)) == expected
        assert registry.get_parser(Path(name)).name == "docling"
    assert registry.list_parsers(Path("note.md")) == [{"name": "text", "is_default": True}]


def test_resolve_parser_name_falls_back_when_stored_parser_is_unavailable(monkeypatch, caplog):
    monkeypatch.setattr(parsers, "registry", ParserRegistry([StubParser("first"), StubParser("alternative")]))
    source = Path("file.custom")

    assert resolve_parser_name(source, "alternative") == "alternative"
    assert resolve_parser_name(source, None) is None
    assert resolve_parser_name(source, "") is None
    # Alembic's fileConfig (test_database_postgres) disables loggers created before it.
    monkeypatch.setattr(parsers.logger, "disabled", False)
    with caplog.at_level(logging.WARNING, logger=parsers.__name__):
        assert resolve_parser_name(source, "llamaparse") is None
    assert "không còn khả dụng" in caplog.text


def test_loader_uses_stored_parser_choice_per_document(monkeypatch, tmp_path):
    first = StubParser("first")
    alternative = StubParser("alternative")
    monkeypatch.setattr(parsers, "registry", ParserRegistry([TextParser(), first, alternative]))
    chosen = tmp_path / "chosen.custom"
    default = tmp_path / "default.custom"
    removed = tmp_path / "removed.custom"
    for path in (chosen, default, removed):
        path.write_bytes(b"data")
    stored = {chosen: "alternative", removed: "llamaparse"}

    documents = {doc.path.name: doc for doc in load_documents(tmp_path, parser_for=stored.get)}

    assert documents["chosen.custom"].text == "# Parsed by alternative\n"
    assert documents["chosen.custom"].parser_name == "alternative"
    assert documents["default.custom"].parser_name == "first"
    assert documents["removed.custom"].parser_name == "first"
    assert alternative.calls == [(chosen, True)]

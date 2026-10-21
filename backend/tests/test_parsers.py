from pathlib import Path

import pytest

import app.parsers as parsers
from app.ingestion.loaders import load_documents
from app.ingestion.uploads import prepare_upload
from app.parsers import DocumentParseError, read_document_text
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
    [
        ("file.doc", None, ".doc"),
        ("file", None, "không có"),
        ("file.md", "missing", "missing"),
        ("file.pdf", "text", "text"),
    ],
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

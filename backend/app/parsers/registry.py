"""Route source formats to default or explicitly selected parser implementations."""

from collections.abc import Iterable
from pathlib import Path

from app.parsers.base import DocumentParseError, DocumentParser


class ParserRegistry:
    def __init__(self, parsers: Iterable[DocumentParser] = ()) -> None:
        self._parsers: dict[str, DocumentParser] = {}
        self._defaults: dict[str, str] = {}
        for parser in parsers:
            self.register(parser)

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset(self._defaults)

    def register(self, parser: DocumentParser, *, default: bool = False) -> None:
        """First registration wins per suffix unless default=True is explicit."""
        if not parser.name or parser.name in self._parsers:
            raise ValueError(f"Parser name is empty or already registered: {parser.name!r}")
        if not parser.extensions or any(
            not suffix.startswith(".") or suffix != suffix.lower() for suffix in parser.extensions
        ):
            raise ValueError("Parser extensions must be nonempty, lowercase suffixes starting with '.'.")
        self._parsers[parser.name] = parser
        for suffix in parser.extensions:
            if default or suffix not in self._defaults:
                self._defaults[suffix] = parser.name

    def list_parsers(self, path: Path) -> list[dict]:
        suffix = path.suffix.lower()
        items = []
        for parser in self._parsers.values():
            if suffix not in parser.extensions:
                continue
            item = {"name": parser.name, "is_default": self._defaults.get(suffix) == parser.name}
            variants = getattr(parser, "variants", None)
            if variants:
                item["variants"] = list(variants)
                item["default_variant"] = parser.default_variant
            items.append(item)
        return items

    def get_parser(self, path: Path, *, parser_name: str | None = None) -> DocumentParser:
        """parser_name may pin a variant as "<name>:<variant>", e.g. "llamaparse:agentic"."""
        suffix = path.suffix.lower()
        if parser_name is None:
            parser_name = self._defaults.get(suffix)
            if parser_name is None:
                raise DocumentParseError(f"Định dạng {suffix or '(không có)'} chưa được hỗ trợ.")
        base_name, _, variant = parser_name.partition(":")
        parser = self._parsers.get(base_name)
        if parser is None:
            raise DocumentParseError(f"Parser {base_name!r} chưa được đăng ký.")
        if variant:
            if variant not in (getattr(parser, "variants", None) or ()):
                raise DocumentParseError(f"Parser {base_name!r} không có tùy chọn {variant!r}.")
            parser = parser.with_variant(variant)
        if suffix not in parser.extensions:
            raise DocumentParseError(f"Parser {parser_name!r} không hỗ trợ định dạng {suffix or '(không có)'}.")
        return parser

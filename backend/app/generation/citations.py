import re


def public_citations(contexts: list[dict]) -> list[dict]:
    """Build deduplicated citations without exposing paths or internal identifiers."""
    citations: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for _, citation in numbered_contexts(contexts):
        key = _citation_key(citation)
        if key not in seen:
            seen.add(key)
            citations.append(citation)

    return citations


def numbered_contexts(contexts: list[dict]) -> list[tuple[int, dict]]:
    """Attach stable citation numbers to contexts, sharing numbers for the same section."""
    citation_numbers: dict[tuple[str, str, str], int] = {}
    numbered: list[tuple[int, dict]] = []

    for context in contexts:
        citation = _citation_metadata(context)
        key = _citation_key(citation)
        number = citation_numbers.setdefault(key, len(citation_numbers) + 1)
        citation["citation_id"] = number
        numbered.append((number, citation))

    return numbered


def _citation_metadata(context: dict) -> dict:
    source_name = _safe_source_name(context.get("source_name") or context.get("source"))
    section_path = str(context.get("section_path") or "").strip()
    heading = str(context.get("heading") or "").strip()
    text = str(context.get("text") or "")
    article = _extract_article(heading, section_path, text)
    clauses = _extract_numbered_units(text, r"(\d{1,2})[.)]")
    points = _extract_numbered_units(text, r"([a-zđ])[.)]") if article or clauses else []
    locator = _build_locator(article, clauses, points, heading, section_path)
    return {
        "citation_id": 0,
        "source_name": source_name,
        "heading": heading or None,
        "section_path": section_path or None,
        "article": article,
        "clauses": clauses,
        "points": points,
        "locator": locator,
    }


def _citation_key(citation: dict) -> tuple[str, str, str]:
    return (
        citation["source_name"].casefold(),
        str(citation.get("section_path") or citation.get("heading") or "").casefold(),
        str(citation.get("locator") or "").casefold(),
    )


def _extract_article(heading: str, section_path: str, text: str) -> str | None:
    for candidate in (heading, section_path, *text.splitlines()[:8]):
        cleaned = _clean_legal_text(candidate)
        match = re.search(r"\bĐiều\s+\d+[a-zA-Z]?\s*[.:]?\s*[^>]{0,220}", cleaned, re.IGNORECASE)
        if match:
            return match.group(0).strip(" .:")
    return None


def _extract_numbered_units(text: str, marker_pattern: str) -> list[str]:
    pattern = re.compile(rf"(?m)^\s*(?:[-*]\s*)?(?:\*\*)?{marker_pattern}\s+")
    values: list[str] = []
    for match in pattern.finditer(text):
        value = match.group(1).casefold()
        if value not in values:
            values.append(value)
    return values[:12]


def _build_locator(
    article: str | None,
    clauses: list[str],
    points: list[str],
    heading: str,
    section_path: str,
) -> str | None:
    base = article or heading or (section_path.rsplit(" > ", 1)[-1] if section_path else "")
    details: list[str] = []
    if clauses:
        details.append(f"Khoản {', '.join(clauses)}")
    if points:
        details.append(f"Điểm {', '.join(points)}")
    if base and details:
        return f"{base} — {'; '.join(details)}"
    return base or ("; ".join(details) if details else None)


def _clean_legal_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[#*_`]+", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _safe_source_name(value: object) -> str:
    """Reduce either Windows or POSIX paths to a display-safe filename."""
    normalized = str(value or "").replace("\\", "/").rstrip("/")
    return normalized.rsplit("/", 1)[-1] or "Tài liệu"

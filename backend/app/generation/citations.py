def public_citations(contexts: list[dict]) -> list[dict]:
    """Build deduplicated citations without exposing paths or internal identifiers."""
    citations: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for _, citation in numbered_contexts(contexts):
        key = _citation_key(citation)
        if key not in seen:
            seen.add(key)
            citations.append(citation)

    return citations


def numbered_contexts(contexts: list[dict]) -> list[tuple[int, dict]]:
    """Attach stable citation numbers to contexts, sharing numbers for the same section."""
    citation_numbers: dict[tuple[str, str], int] = {}
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
    return {
        "citation_id": 0,
        "source_name": source_name,
        "heading": heading or None,
        "section_path": section_path or None,
    }


def _citation_key(citation: dict) -> tuple[str, str]:
    return (
        citation["source_name"].casefold(),
        str(citation.get("section_path") or citation.get("heading") or "").casefold(),
    )


def _safe_source_name(value: object) -> str:
    """Reduce either Windows or POSIX paths to a display-safe filename."""
    normalized = str(value or "").replace("\\", "/").rstrip("/")
    return normalized.rsplit("/", 1)[-1] or "Tài liệu"

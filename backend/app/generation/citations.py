def public_citations(contexts: list[dict]) -> list[dict]:
    """Build deduplicated citations without exposing paths or internal identifiers."""
    citations: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for context in contexts:
        source_name = _safe_source_name(context.get("source_name") or context.get("source"))
        section_path = str(context.get("section_path") or "").strip()
        heading = str(context.get("heading") or "").strip()
        citation_key = (source_name.casefold(), (section_path or heading).casefold())
        if citation_key in seen:
            continue

        seen.add(citation_key)
        citations.append(
            {
                "source_name": source_name,
                "heading": heading or None,
                "section_path": section_path or None,
            }
        )

    return citations


def _safe_source_name(value: object) -> str:
    """Reduce either Windows or POSIX paths to a display-safe filename."""
    normalized = str(value or "").replace("\\", "/").rstrip("/")
    return normalized.rsplit("/", 1)[-1] or "Tài liệu"

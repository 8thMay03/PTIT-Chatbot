from app.ingestion.legal_units import extract_legal_units


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
    text = str(context.get("evidence_text") or context.get("text") or "")
    units = extract_legal_units(heading, section_path, text)
    article, clauses, points = units.article, units.clauses, units.points
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


def _safe_source_name(value: object) -> str:
    """Reduce either Windows or POSIX paths to a display-safe filename."""
    normalized = str(value or "").replace("\\", "/").rstrip("/")
    return normalized.rsplit("/", 1)[-1] or "Tài liệu"

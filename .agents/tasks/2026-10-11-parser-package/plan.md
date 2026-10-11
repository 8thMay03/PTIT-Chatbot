# Plan

- Coordinator, implementer, verifier and reviewer: `/root`; review is `self_review`.
- S-1 (done): Define parser contract and add registry tests for format routing, named alternatives, unsupported input and dynamic format discovery. Files: new `backend/tests/test_parsers.py`.
- S-2 (done; depends S-1): Extract `base.py`, `registry.py`, `text.py`, `docling.py`, public facade `__init__.py` under `backend/app/parsers/`. Keep a public-import compatibility shim in `backend/app/ingestion/converters.py`; preserve existing user change in the moved implementation.
- S-3 (done; depends S-2): Migrate ingestion/API and tests to parser imports. Files: `backend/app/ingestion/{pipeline,loaders,uploads}.py`, `backend/app/api/routes.py`, `backend/tests/test_document_{api,converters,pipeline}.py`.
- S-4 (done; depends S-2/S-3): Document extension mechanism; verify parser/document suites and isolated Docker flow; inspect final diff and self_review. Files: `README.md`, task documents.
- Contract: `DocumentParser` exposes `name`, `extensions`, `parse(path, *, convert=True) -> str | None`. `ParserRegistry` registers parsers, selects a default per suffix or an explicit implementation by name, and exposes supported suffixes. `read_document_text` remains the facade; `convert=False` must never trigger expensive conversion. Shared `DocumentParseError`; legacy `DocumentConversionError` aliases the same type. Docling cache remains implementation-specific and keeps existing key semantics.

# Implementation

- Owner: `/root`
- Baseline: main at `a081ee8`, with one user edit in the existing converter's CUDA warning. No agent source changes yet.
- Chosen structure: top-level `app/parsers` independent of ingestion, with reusable registry and per-parser conversion/cache behavior. Format support in loaders/uploads will read the registry rather than depend on Docling-specific constants.

## Implementation progress

- Added `DocumentParser` protocol and shared `DocumentParseError`, `ParserRegistry`, `TextParser`, `DoclingParser`, and a common `read_document_text` facade. Registry supports suffix defaults, explicit named alternatives and dynamic supported-format discovery.
- Moved the Docling converter/cache implementation into `app/parsers/docling.py`, preserving the user's exact `cu13  0` string edit. Kept lazy model loading, locks, raw cache version/key/options, table/bold post-processing and cache-only preview behavior.
- Migrated ingestion and API to parser facade/error imports. Upload signature checks remain for PDF/DOCX, UTF-8 validation remains for MD/TXT; newly registered binary formats are validated by their own parser rather than forced through text decoding. Loaders/uploads discover suffixes dynamically.
- `app.ingestion.converters` remains a public-import compatibility shim; its legacy error name aliases the shared parser error. Internal tests now patch the actual Docling implementation module.
- New parser suite initially failed collection because `app.parsers` did not exist. After extraction, parser + document suites: 65 passed.
- README describes package responsibilities, parser registration, named selection, conversion-free previews and the current default-only UI integration.

## Integrated verification and handoff

- Final parser/document suite: 66 passed. Added an explicit pre-extraction Docling cache fixture to prove the old cache filename still serves previews without conversion.
- Docker's six integrity groups passed after extraction with real Docling DOCX parsing and PostgreSQL/pgvector. Existing public imports in the Docker harness remain compatible. Temporary schemas/source trees are cleaned up by the harness; test embeddings are hash vectors with 1,536 dimensions.
- Compose health is OK and source changes are active through the existing bind mount/reloader. No DB migration, user knowledge-base rebuild or UI selector added.
- The user's `cu13  0` warning string is preserved at `app/parsers/docling.py`. Production code no longer imports the legacy converter module; only the compatibility test does.
- Work is uncommitted on local main for user review. Remaining full-suite fixture failures are pre-existing and documented separately.

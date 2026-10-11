# Verification

- AC-1 / AC-2 / AC-3 / AC-4: not_run for this fix.
- Earlier full-suite baseline at `624f12c`: 143 passed, 7 failed, 20 errors. Missing `data/so-tay-sinh-vien-d21.md` and `data/test_chunker_tables _1_.md` explain 6 failures + 20 errors; one converter logging test also fails only in the full suite. These are separate from the three requested production defects.
- Docker checks must use isolated DB/source fixtures; do not run a destructive full rebuild on the user's knowledge base.

## Final evidence

- AC-1: passed — ten parametrized cases cover new/replacement uploads failing at conversion, embeddings, DB flush, source publication, or DB commit. Assert original source bytes/existence, document/chunk snapshots, unchanged vector-store calls, and temporary cleanup. Two successful PDF/DOCX replacement cases assert final source identity, metadata, size, new content and one conversion per upload. Existing moved-path identity regressions also pass.
- AC-2: passed — rebuild failure preserves the entire indexed snapshot without embedding or vector reset; loader rejects empty files and conversion errors with filenames, ignores unsupported formats; API returns 422; valid rebuild still succeeds.
- AC-3: passed — updated padding test plus cached/uncached cases preserve repeated numeric, zero and text values. Docker real DOCX table also retains `| 100 | 100 |`.
- Regression run before application fix: 15 failed, 27 passed, demonstrating the source loss, partial rebuild, table corruption and missing API failure mapping.
- Final automated command (cwd `backend`, `EMBEDDING_PROVIDER=hash`, `DATABASE_URL=sqlite://`): `.venv/Scripts/python.exe -m pytest tests/test_document_pipeline.py tests/test_document_api.py tests/test_document_repositories.py tests/test_document_converters.py tests/test_document_uploads.py -q --tb=short` -> **55 passed**, one existing Starlette/httpx deprecation warning.
- Full suite with the same environment: `.venv/Scripts/python.exe -m pytest tests -q --tb=no` -> **164 passed, 6 failed, 20 errors**. The 6 failures need `data/test_chunker_tables _1_.md`; the 20 errors need `data/so-tay-sinh-vien-d21.md`. No production-code failure remains in this run. CUDA logging fixture isolation fixed the seventh baseline failure.
- Docker command: `Get-Content -Raw C:/Users/khanh/AppData/Local/Temp/ptit-ingestion-integrity-check.py | docker exec -i ptitchatbot-backend-1 python -` -> six groups passed. Real Docling parsing, real PostgreSQL tables and pgvector values; test hash embeddings with 1,536 dimensions. Temporary schema search path explicitly asserted; sources and cache in a temporary directory. No external embeddings provider called.
- Docker groups: initial real DOCX/table parsing; failed replacement/new upload; embedding failure; commit rollback; failed rebuild 422 with snapshot preservation; successful replacement and rebuild.
- Cleanup assertions: zero remaining `ingestion_integrity_*` schemas. User DOCX `fba6a27b28bd1dfa30a0a8c35849874f6b881e0dbc14ce8d43cd1c97257d7593` remains present with four chunks and consistent metadata ID. Backend health endpoint reports connected PostgreSQL.
- `git diff --check`: passed. AC-4 verification passed; final self_review approved on the application/test/README blobs listed in `review.md`. Remaining full-suite fixture failures are outside the three requested defects and explicitly reported.

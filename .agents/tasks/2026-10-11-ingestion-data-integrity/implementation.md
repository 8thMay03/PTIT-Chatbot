# Implementation

- Owner: `/root`
- Baseline: clean worktree at `624f12c`. The previous merge assessment reproduced all three defects in isolated temporary fixtures.
- No application code changed yet. Plan favors aborting a failed rebuild instead of silently applying a partial knowledge base.

## Implementation progress

- Added regressions first: the initial run had 15 failures and 27 passes, including the three original production defects and the planned failure boundaries.
- Uploads now parse in an external temporary directory. Shared ingestion builds records against the final source path and staged file size, computes embeddings and flushes DB changes, then publishes the source around commit. Publication uses destination-filesystem atomic rename plus a rollback backup; failed new uploads remove the published source. Temporary names have no supported document suffix.
- Rebuild loading fails with the source filename for conversion/read/encoding errors and empty supported files. No DB replacement, vector reset or embedding begins on parse failure. `/api/ingest` maps the failure to 422.
- Removed inference of merged cells from equal Markdown values. Raw cache exports are retained, so the corrected post-processing applies without a converter cache version bump.
- Initial corrected document suite: 51 passed. Added further DB-flush and file-publication failure coverage, and isolated the existing CUDA logging test from Alembic's logger-disabling side effect before broader verification.

## Integrated result and handoff

- Final document suite: 55 passed. Full backend suite: 164 passed, 6 failed, 20 errors; all remaining failures/errors are the existing missing benchmark/handbook data fixtures.
- Docker verification passed six groups with real Docling DOCX parsing and PostgreSQL/pgvector, using a unique temporary schema and source tree. Test embeddings were 1,536-dimensional hash vectors to avoid external API calls. Tested failed replacement/new conversion, embedding failure, commit rollback, failed rebuild 422, equal cells, and successful replacement/rebuild.
- The first Docker harness run failed due to treating list-valued embeddings as NumPy arrays; corrected the harness to use `list()` and reran successfully. All temporary schemas/trees were cleaned up.
- Current Compose backend picked up the source changes through its existing reload bind mount; health is OK. The user's previously affected DOCX still exists with four chunks and its original ID.
- README documents source rollback, strict rebuild, 422 errors and literal table-value preservation. No DB migration needed. Work remains uncommitted for user review; no main merge performed.

# Verification

- AC-1 / AC-2 / AC-3: not_run — regression tests pending.
- AC-4: not_run — live Docker reparse pending.
- Known baseline: unrelated temporary-path preview/deletion tests previously failed; report separately if encountered, without attributing them to this change.

## Final checks

- AC-1 / AC-2: passed — three parametrized moved-file regression cases cover explicit reparse before and after GET source-path repair, plus implicit ingestion after repair. Assert one document, retained ID/created_at, new content, consistent chunk foreign keys/metadata/vector payloads, and old vector deletion.
- AC-3: passed — API regression checks existing ID propagation. Before the fix, all four new cases failed; the implicit case reproduced the unique constraint error.
- Automated command (cwd `backend`, `EMBEDDING_PROVIDER=hash`, `DATABASE_URL=sqlite://`): `.venv/Scripts/python.exe -m pytest tests/test_document_pipeline.py tests/test_document_api.py tests/test_document_repositories.py tests/test_document_converters.py tests/test_document_uploads.py -q --tb=short`.
- Final result: **35 passed**, one existing Starlette/httpx deprecation warning. Initial broad run had three known fixture failures; corrected isolation in those tests and reran the same suite successfully.
- AC-4: passed — real `POST http://127.0.0.1:8000/api/documents/fba6a27b28bd1dfa30a0a8c35849874f6b881e0dbc14ce8d43cd1c97257d7593/parse` succeeded for `4. Đăng ký và mua BHYT.docx`. Response retained that ID, source `data/raw/4. Đăng ký và mua BHYT.docx`, chunk_count 4.
- PostgreSQL assertions passed: one document for that path; four chunks; document/chunk metadata all reference the retained ID/current source; all vectors have 1,536 dimensions; old `data/4.*` chunk count zero.
- Frontend proxy `GET http://127.0.0.1:5173/api/documents/<id>` passed: same ID, four chunks, full text length 2,421 characters.
- Compose backend and PostgreSQL healthy; frontend running.
- `git diff --check`: passed. Full repository suite not run; scope-specific document suite and real Docker flow verified.

# Verification

- AC-1 / AC-2 / AC-3 / AC-4: not_run.
- Known previous baseline: document suite 55 passed; Docker six groups passed; full backend suite 164 passed, 6 failures and 20 errors due to missing two data fixtures.
- Preserve and verify the pre-existing user CUDA string change after extraction.

## Final evidence

- AC-1: passed — registry tests cover suffix routing (case-insensitive), named alternatives, explicit default replacement, unsupported formats/names, duplicate-name rejection, forwarding preview flags, and newly registered binary formats recognized by both upload validation and loaders.
- AC-2: passed — implementation lives in `backend/app/parsers/{base,registry,text,docling,__init__}.py`. Production ingestion/API imports parser facade; `rg` finds old converter imports only in its compatibility test. Dynamic supported-extension discovery works without editing ingestion for new formats.
- AC-3: passed — existing document tests still pass. Legacy public read/conversion imports and error alias are tested. The fixed historical raw cache filename `03ac7ad915a49a86bfdef44e4408d17efca6fb67432052aa1e38fafb04da24c1.md` serves a preview with zero converter calls. OCR/device options, cache key/version and conversion locks are retained. User CUDA string change `cu13  0` verified in `backend/app/parsers/docling.py`.
- Targeted command (cwd `backend`, `EMBEDDING_PROVIDER=hash`, `DATABASE_URL=sqlite://`): `.venv/Scripts/python.exe -m pytest tests/test_parsers.py tests/test_document_pipeline.py tests/test_document_api.py tests/test_document_repositories.py tests/test_document_converters.py tests/test_document_uploads.py -q --tb=short` -> **66 passed**, one existing Starlette/httpx deprecation warning.
- Full-suite command with the same environment: `.venv/Scripts/python.exe -m pytest tests -q --tb=no` -> **175 passed, 6 failed, 20 errors**. All remaining failures/errors are the existing missing `data/test_chunker_tables _1_.md` and `data/so-tay-sinh-vien-d21.md` fixtures, matching the baseline categories.
- Docker command: `Get-Content -Raw C:/Users/khanh/AppData/Local/Temp/ptit-ingestion-integrity-check.py | docker exec -i ptitchatbot-backend-1 python -` -> six groups passed after extraction: real Docling/table parsing, failed new/replacement upload, embedding failure, commit rollback, failed rebuild 422 with unchanged index, successful replacement/rebuild. Real PostgreSQL/pgvector in an isolated temporary schema/tree; test hash embeddings (1,536 dimensions), no external embedding calls.
- Compose backend health: HTTP 200, PostgreSQL connected. `git diff --check`: passed.
- AC-4 verification passed; final self_review approved on the final implementation/cache-test/README blobs listed in `review.md`. Full repository suite is explicitly not green because of the data fixtures above.

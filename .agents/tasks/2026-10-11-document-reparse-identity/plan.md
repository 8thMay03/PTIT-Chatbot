# Plan

- Owner for all work: `/root`; reviewer: `/root` (`self_review`).
- S-1 (done): Add regression tests, then resolve stored identity before building ingestion records. Files: `backend/app/ingestion/pipeline.py`, `backend/app/db/repositories.py`, `backend/tests/test_document_pipeline.py`.
- S-2 (done, depends S-1): Pass existing ID through parse API and cover API contract. Files: `backend/app/api/routes.py`, `backend/tests/test_document_api.py`.
- S-3 (done, depends S-1/S-2): Run targeted tests, verify actual Docker reparse, inspect final diff and record self_review.
- Contract: `ingest_path(path, *, document_id=None)` uses the explicit existing ID for reparses; otherwise resolves an existing record by source path before deriving a new ID. Document rows, chunk foreign keys, metadata and vector cleanup share this identity.

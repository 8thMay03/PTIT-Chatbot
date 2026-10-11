# Implementation

- Owner: `/root`
- Initial diagnosis: GET detail synchronizes the moved source path but preserves the historical ID. Reparse hashes the new path, tries to insert another document, and hits the unique source-path constraint.
- Work has not yet changed application code. Working tree was clean at task start.

## S-1 / S-2 implementation

- Added four regression cases first; all failed against the original implementation. The implicit moved-path case reproduced the unique source-path constraint failure, and the API test showed the historical ID was not forwarded.
- Added a repository lookup for stored identity by source path. Single-document ingestion uses an explicit ID for reparse or resolves a registered path before generating records.
- Record construction propagates the canonical ID to the document, chunk foreign keys and metadata/vector payloads. Existing vector cleanup now naturally targets the original document.
- Parse API passes the stored document ID. No schema or user-data migration is needed.

## Verification and handoff

- Corrected three pre-existing test-fixture failures in the touched test files: deletion's temporary project root, and preview mocks for two API unit tests. These changes isolate unit tests from real source lookup/database access; production preview/deletion behavior is unchanged.
- Relevant suite: 35 passed. Running Compose backend reloaded the bind-mounted source automatically.
- Actual DOCX reparse succeeded using real configured OpenAI embeddings and PostgreSQL; the historical document ID was retained, four fresh chunks replaced the old paths, and the source has exactly one document row.
- Frontend proxy detail request returned all 2,421 characters of full text and four chunks.
- Initial PowerShell request to `localhost` did not reach the backend; direct `127.0.0.1` with proxy bypass succeeded. This is a host request-path issue, separate from ingestion.
- Handoff to user: fix is active in the running Docker backend; no rebuild or database reset is required for the current bind-mounted Compose setup.

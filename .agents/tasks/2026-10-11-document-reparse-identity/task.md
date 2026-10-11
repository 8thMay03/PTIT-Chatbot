# Document reparse identity

- Coordinator: `/root`
- Status: done
- Request: Fix DOCX reparse failing with duplicate `documents.source_path` after a source file moves.
- Scope: Single-document ingestion identity, parse API, regression tests; verify the affected DOCX on the running Docker stack. No schema migration or full knowledge-base rebuild.
- AC-1: Reparse retains the existing document ID after a source-path change and replaces its chunks/vectors consistently.
- AC-2: Ingestion by an already registered source path reuses its stored ID rather than inserting a duplicate.
- AC-3: Parse API propagates the requested document ID; relevant automated checks pass.
- AC-4: The affected real DOCX reparses successfully on Docker without a duplicate document.

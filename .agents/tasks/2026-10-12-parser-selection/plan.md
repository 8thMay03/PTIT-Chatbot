# Plan
Owner: codex (coordinator, implementation, verification, self_review).
S-1: Registry discovery + document parser GET endpoint + optional parser_name query parameter; pipeline forwards selection. Files: registry.py, routes.py, pipeline.py.
S-2: Shared ParserSelectionModal wired into list/detail through DatasetView; default selected; loading/error/retry; retain existing parsing status.
S-3: API/registry tests, backend regression suite, frontend build, self_review.
Contract: GET /documents/{id}/parsers -> {parsers:[{name,is_default}]}; POST /documents/{id}/parse?parser_name=...; omitted name preserves defaults.

S-1/S-2/S-3: done. Browser interaction remains not_run and reported as verification limitation.

S-4 codex in_progress: UI refinement scoped to ParserSelectionModal.jsx and dedicated parser-selection.css; verification/build and self_review. No shared Modal API changes.

S-4: done; build and self_review complete, browser verification limitation documented.

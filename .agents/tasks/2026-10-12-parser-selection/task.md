# Parser selection
Coordinator: codex
Status: in_progress
AC-1: API lists compatible parsers/default and accepts explicit selection without breaking existing calls.
AC-2: Parse actions in list and detail open a selection dialog; only confirmation starts parsing.
AC-3: Regression tests/build pass and self_review approved.
Scope excludes upload/rebuild selection. Preserve existing user deletion in documents/.

Status: done. Acceptance evidence and UI verification limits recorded in verification.md; self_review approved.

UI refinement requested: status in_progress; retain API contract. AC-4: accessible parser cards, document context, consistent actions and responsive states.

UI refinement status: done; AC-4 verified by build/code review, browser check not_run.

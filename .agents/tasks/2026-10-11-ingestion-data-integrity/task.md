# Ingestion data integrity

- Coordinator: `/root`
- Status: done
- Request: Plan and fix the three merge blockers: destructive failed upload replacement, partial rebuild deleting indexed documents, and deduplication of independent equal table cells.
- Scope: ingestion upload publication, loader/rebuild failure behavior and API error, Markdown table normalization, regression tests and relevant documentation. Preserve existing document identity fix. No main merge, no full rebuild of user data, no schema changes.
- AC-1: Failed conversion/embedding/database persistence of an upload leaves the original source and indexed data intact; failed new uploads leave no source; successful uploads use final source identity/size and clean up temporary files.
- AC-2: A supported file that fails parsing or has no text aborts rebuild before DB/vector replacement and surfaces a useful API error naming the file. A valid rebuild still succeeds.
- AC-3: Equal values in separate table cells remain intact, including when reading existing raw conversion cache; padding/separator normalization still works.
- AC-4: Regression tests prove each original defect, relevant suites pass, and final self_review has no mandatory open findings. Report unrelated full-suite failures separately.

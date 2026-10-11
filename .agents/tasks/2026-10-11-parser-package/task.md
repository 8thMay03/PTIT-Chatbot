# Parser package extraction

- Coordinator: `/root`
- Status: done
- Request: Separate parsers into their own folder to support multiple parser implementations later.
- Scope: `backend/app/parsers/`, parser imports in ingestion/API, relevant tests and README. Keep ingestion/chunking/embedding responsibilities separate. No UI parser selector, schema changes, commit or merge requested.
- Existing user change: `backend/app/ingestion/converters.py` has an uncommitted CUDA warning URL string change (`cu13  0`); preserve it exactly in the moved Docling implementation.
- AC-1: Parser interface and registry support extension defaults and explicit parser-name selection, including alternative parsers for one format.
- AC-2: Text and Docling implementations live in `app/parsers`; ingestion/API use a common parser entry point and discover supported extensions from the registry.
- AC-3: Existing read API, error compatibility, raw cache keys, OCR/device settings, read-only preview behavior and recent ingestion integrity fixes are retained. Preserve the user's source edit.
- AC-4: Relevant automated suites and isolated real-Docling Docker checks pass; final self_review has no mandatory open findings. Report existing full-suite fixture issues separately.

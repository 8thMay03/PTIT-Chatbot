# Verification
AC-1/2/3: not_run.

AC-1 passed: 68 parser/document regression tests, including compatible/default discovery, missing document, explicit selection forwarding and 422 error. Command: backend/.venv python -m pytest targeted six suites with EMBEDDING_PROVIDER=hash DATABASE_URL=sqlite://.
AC-2: code review confirms both entry points open shared dialog, POST only on confirmation; cancel, loading/error/retry/empty states implemented. Browser interaction not run.
AC-3 passed: npm run build; git diff --check. Existing full-suite fixture issues not rerun.

AC-4 passed (build + code inspection): npm run build succeeds; git diff --check succeeds. Native radio keyboard behavior, disabled fieldset while busy and focus styling reviewed. Browser visual/interaction testing not_run.

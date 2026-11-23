# Kế hoạch: rerank-provider-allowlist

## Nhiệm vụ

### S-01 — `claude-agent` — `done`

- Phạm vi file: `backend/app/core/config.py`, `backend/tests/test_llm_url_allowlist.py`,
  `frontend/src/models/catalog.js`, `.env.example`, `README.md`.
- Nội dung: hằng `_BUILTIN_RERANK_API_ORIGINS` thêm vào `_default_llm_url_allowlist()`; cập nhật test, gợi ý, tài liệu.
- Phụ thuộc: không.

## Review

- Reviewer: `claude-agent` (`self_review`).

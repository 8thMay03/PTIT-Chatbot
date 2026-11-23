# Triển khai: rerank-provider-allowlist

- Nhánh `feat/rerank-provider-allowlist` (tách từ `dev` tại `b496054`).

## S-01 — `claude-agent` — `done` — 2026-11-23T23:25:01+07:00

- `backend/app/core/config.py`: `_BUILTIN_RERANK_API_ORIGINS = (https://api.cohere.com, https://api.cohere.ai,
  https://api.jina.ai)`, nằm sau `https://api.openai.com` trong allowlist mặc định.
- `backend/tests/test_llm_url_allowlist.py`: cập nhật danh sách mặc định; thêm 2 test (mặc định chấp nhận/từ chối,
  allowlist đặt giá trị không kèm origin dựng sẵn).
- `frontend/src/models/catalog.js`: gợi ý Base URL nêu Cohere/Jina được phép sẵn.
- `.env.example`, `README.md`: mô tả allowlist mặc định mới (kèm `RERANKER_BASE_URL` vốn đã có từ task api-reranker).

## Quyết định

- I-01: Chỉ thêm khi allowlist trống, giữ ngữ nghĩa "đặt giá trị = danh sách tuyệt đối" cho người vận hành muốn chặt.
- I-02: Origin HTTPS công khai cố định của nhà cung cấp không mở đường SSRF vào mạng nội bộ; khoá API chỉ gửi tới
  đúng origin admin nhập.
- I-03: Không thêm Voyage: API trả `data`/nhận `top_k`, không khớp client chuẩn Cohere hiện có.

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

- Người gửi: `claude-agent`; người nhận: người dùng.
- Chưa commit. Container backend cần khởi động lại để nạp `config.py`.

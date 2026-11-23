# Task: Cho phép sẵn dịch vụ rerank công khai (Cohere, Jina)

- ID: `2026-11-23-rerank-provider-allowlist`
- Trạng thái: `in_review`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng
- Tạo lúc: `2026-11-23T23:25:01+07:00`
- Cập nhật lúc: `2026-11-23T23:25:01+07:00`

## Yêu cầu và kết quả mong muốn

Profile reranker `rerank_api` nhập Base URL `https://api.jina.ai/v1` hoặc `https://api.cohere.com/v2` bị từ chối
"Host '...' không nằm trong LLM_BASE_URL_ALLOWLIST." vì allowlist mặc định chỉ có `api.openai.com` và origin trong
`.env`. Cần dùng được Cohere/Jina từ giao diện mà không phải sửa `.env`.

## Phạm vi

- Bao gồm: allowlist mặc định trong `backend/app/core/config.py`, test, gợi ý trong `frontend/src/models/catalog.js`,
  `.env.example`, `README.md`.
- Ngoài phạm vi: nhà cung cấp không theo chuẩn Cohere (Voyage trả `data`/`top_k`); đổi cách so khớp allowlist.
- Ràng buộc: `LLM_BASE_URL_ALLOWLIST` đặt giá trị vẫn thay thế toàn bộ mặc định; chỉ thêm origin HTTPS cố định.

## Tiêu chí nghiệm thu

- [x] AC-01: Allowlist trống chấp nhận `https://api.jina.ai`, `https://api.cohere.com`, `https://api.cohere.ai`
  (cổng 443), từ chối http, cổng khác và subdomain.
- [x] AC-02: Allowlist đặt giá trị không tự thêm các origin trên.
- [x] AC-03: Test backend và frontend không hồi quy.

## Tài liệu và phụ thuộc

- `.agents/tasks/2026-11-21-api-reranker` (bàn giao ghi admin phải tự thêm origin rerank).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai, kiểm chứng và self review.
- Blocker: không có.
- Bước tiếp theo: người dùng commit/PR vào `dev` khi muốn.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-23T23:25:01+07:00 — claude-agent: tạo task, chuyển `in_review` sau khi kiểm chứng.

# Plan: 2026-11-12-chunk-pagination-fix

## Phân công

### S-01 — Sửa phân trang đoạn và thêm test hồi quy

- Agent: `claude-code`
- Trạng thái: `in_review`
- Mục tiêu: chuyển trang không bị kéo về trang 1; phục vụ `AC-01`, `AC-02`.
- Phạm vi file được sửa: `frontend/src/DocumentView.jsx`, `frontend/src/DocumentView.pagination.test.jsx`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: diff trên nhánh `feat/chunk-pagination-fix`.
- Người nhận: người dùng.

## Hợp đồng dùng chung

- Không áp dụng (không đổi API hay query key).
- File mã nguồn dùng chung và người sửa: `frontend/src/DocumentView.jsx` — `claude-code`.
- Lượt ghi năm file task: chỉ `claude-code` ghi.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: AC-01, AC-02.
- Reviewer: `claude-code`; phạm vi: diff của S-01.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-code`.

## Thứ tự tích hợp và kiểm chứng

1. Sửa `DocumentView.jsx` và thêm test.
2. Chạy test mới, xác nhận test thất bại khi bỏ bản sửa.
3. Chạy toàn bộ `vitest` và `vite build`.
4. Self-review, ghi `review.md`.

## Rủi ro và điều chỉnh kế hoạch

- `placeholderData` hiển thị trang cũ trong lúc tải trang mới; nút phân trang vẫn bị khóa khi `busy` nên không bấm dồn được.

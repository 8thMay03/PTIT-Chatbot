# Plan: 2026-11-12-chunk-highlight-mapping

## Phân công

### S-01 — Bộ định vị đoạn mới và tích hợp vào DocumentView

- Agent: `claude-code`
- Trạng thái: `in_review`
- Mục tiêu: AC-01, AC-02, AC-03.
- Phạm vi file được sửa: `frontend/src/lib/chunkLocator.js`, `frontend/src/lib/chunkLocator.test.js`, `frontend/src/DocumentView.jsx`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: diff trên nhánh `feat/chunk-highlight-mapping`.
- Người nhận: người dùng.

## Hợp đồng dùng chung

- Không đổi API, query key hay CSS. `createChunkLocator(root).locate(list, position, totalChunks)` là giao diện nội bộ của frontend.
- Lượt ghi năm file task: chỉ `claude-code` ghi.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: AC-01…AC-03.
- Reviewer: `claude-code`; hình thức `self_review`.
- Người xử lý nhận xét: `claude-code`.

## Thứ tự tích hợp và kiểm chứng

1. Đo thuật toán cũ trên D26 (script ngoài repo, dữ liệu export từ DB local).
2. Viết `chunkLocator.js`, đo lại, tinh chỉnh.
3. Tích hợp vào `DocumentView.jsx`, thêm test, chạy `vitest` và `vite build`.

## Rủi ro và điều chỉnh kế hoạch

- Lập chỉ mục tài liệu lớn tốn một lần ở lần trỏ chuột đầu (≈270ms trong jsdom với D26, 412k ký tự sau chuẩn hóa); mỗi lần định vị ≈9ms.

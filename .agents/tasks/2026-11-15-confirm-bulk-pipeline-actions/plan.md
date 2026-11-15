# Plan: 2026-11-15-confirm-bulk-pipeline-actions

Nhánh: `feat/confirm-bulk-pipeline-actions`, tách từ `dev` tại `8c7c78a` (lúc soạn: `0fdd444`).

## Phân công

### S-01 — Thêm modal xác nhận cho ba thao tác hàng loạt

- Agent: `claude-code`
- Trạng thái: `in_review`
- Mục tiêu: menu "Bảo trì" đặt state `pendingMaintenance` (`"rechunk"` hoặc `"reindex"`) rồi mở `Modal`; xác nhận mới gọi `runMaintenance`. "Chia đoạn lại dataset" theo cùng mẫu với `confirmParseAll`. Phục vụ `AC-01`..`AC-06`.
- Phạm vi file được sửa: `frontend/src/datasets/DatasetListView.jsx`, `frontend/src/DatasetView.jsx`, test liên quan (`datasets/DatasetListView.test.jsx`, mới: `DatasetView.chunkConfirm.test.jsx`).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: diff, kết quả vitest, ảnh chụp ba modal.
- Người nhận: `claude-code` (coordinator).

## Hợp đồng dùng chung

- Không đổi API. Dùng lại `components/Modal.jsx`: `tone="danger"` + `danger-btn` cho "Nạp lại toàn bộ"; `default` + `primary-btn` cho hai thao tác chia đoạn (cùng mẫu modal "Parse lại dataset"; chia đoạn không làm mất bản Markdown đã lưu).
- Lượt ghi năm file task: coordinator tổng hợp.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: `AC-01`..`AC-06`.
- Reviewer: `claude-code`; phạm vi: diff S-01.
- Hình thức review: `self_review` (một agent kiêm mọi vai trò).
- Người xử lý nhận xét: agent S-01.

## Thứ tự tích hợp và kiểm chứng

1. S-01 triển khai.
2. Verifier chạy vitest; nếu dựng được backend có dữ liệu thử thì kiểm tra thủ công ba modal trong `/admin#documents`.
3. Review, sửa, kiểm tra lại; coordinator đóng task.

## Rủi ro và điều chỉnh kế hoạch

- `runMaintenance` hiện đóng menu và kiểm tra job parse nền trước khi gọi API. Giữ thứ tự này sau khi xác nhận; nếu còn job nền thì đóng modal và hiện cảnh báo như cũ.

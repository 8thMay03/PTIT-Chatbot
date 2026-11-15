# Plan: 2026-11-15-hide-chunk-placeholder-controls

Nhánh dự kiến: `feat/hide-chunk-placeholder-controls`, tách từ `dev` mới nhất (lúc soạn: `0fdd444`). Plan theo đề xuất mặc định của Q-01, Q-02.

## Phân công

### S-01 — Gỡ điều khiển đoạn chưa có tác dụng

- Agent: `claude-code`
- Trạng thái: `in_review`
- Mục tiêu: gỡ công tắc, ô chọn, "Chọn tất cả", nhãn "Văn bản" và state, handler đi kèm; dọn CSS; phục vụ `AC-01`..`AC-04`.
- Phạm vi file được sửa: `frontend/src/DocumentView.jsx`, `frontend/src/styles/document.css`, test (bổ sung `DocumentView.pagination.test.jsx` hoặc test mới).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: diff, kết quả vitest, ảnh chụp thẻ đoạn sau khi gỡ.
- Người nhận: `claude-code` (coordinator).

## Hợp đồng dùng chung

- Không đổi API.
- `pill-switch` và `chunk-checkbox` có thể còn được dùng ở màn khác (ví dụ `ConfigView` dùng `pill-switch`). Chỉ gỡ CSS sau khi grep xác nhận không còn nơi nào dùng.
- Lượt ghi năm file task: coordinator tổng hợp.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: `AC-01`..`AC-04`.
- Reviewer: `claude-code`; phạm vi: diff S-01.
- Hình thức review: `self_review` (một agent làm cả triển khai, kiểm chứng, review).
- Người xử lý nhận xét: agent S-01.

## Thứ tự tích hợp và kiểm chứng

1. Chốt Q-01, Q-02.
2. S-01 triển khai.
3. Verifier chạy vitest; nếu dựng được backend có tài liệu đã chia đoạn thì kiểm tra thủ công màn chi tiết tài liệu.
4. Review, sửa, kiểm tra lại; coordinator đóng task.

## Rủi ro và điều chỉnh kế hoạch

- Class `selected` trên thẻ đoạn đang dựa vào `selectedChunkIds`; gỡ phải giữ được class `is-hovered-target` và style hover.

# Plan: 2026-11-15-chat-header-dark-bg

Nhánh dự kiến: `feat/chat-header-dark-bg`, tách từ `dev` mới nhất (lúc soạn: `0fdd444`).

## Phân công

### S-01 — Đưa nền header chat về token sáng/tối

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: thêm token nền kính mờ cho header (sáng và cả hai khối tối), dùng trong `.chat-header`; phục vụ `AC-01`..`AC-04`.
- Phạm vi file được sửa: `frontend/src/styles/tokens.css`, `frontend/src/styles/chat.css`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: diff hai file CSS, ảnh chụp header ở giao diện sáng và tối, số đo tương phản.
- Người nhận: `claude-code` (coordinator).

## Hợp đồng dùng chung

- Không áp dụng API. Token mới trong `tokens.css` là giao diện dùng chung: đặt tên theo quy ước token ngữ nghĩa hiện có và ghi vào `implementation.md`.
- File mã nguồn dùng chung và người sửa: `frontend/src/styles/chat.css` cũng nằm trong phạm vi của `2026-11-15-copy-btn-touch-keyboard`. Không sửa song song; task nào nhận trước làm xong thì task kia rebase.
- Lượt ghi năm file task: coordinator tổng hợp.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: `AC-01`..`AC-04`.
- Reviewer: `claude-code`; phạm vi: diff S-01.
- Hình thức review: `self_review` (một agent kiêm mọi vai trò).
- Người xử lý nhận xét: agent S-01.

## Thứ tự tích hợp và kiểm chứng

1. S-01 triển khai trên nhánh riêng.
2. Verifier mở `/chat` ở giao diện sáng, tối theo hệ thống và tối chọn tay; đo tương phản bằng DevTools; chạy `npm test`, `npm run build`.
3. Reviewer ghi nhận xét trong `review.md`; agent sửa; verifier kiểm tra lại.
4. Coordinator đóng task khi đủ điều kiện.

## Rủi ro và điều chỉnh kế hoạch

- Quên thêm token vào một trong hai khối tối thì lỗi chỉ còn ở một cách chọn giao diện. Kiểm tra cả hai cách trong V-01.

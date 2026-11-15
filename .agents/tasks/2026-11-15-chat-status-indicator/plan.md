# Plan: 2026-11-15-chat-status-indicator

Nhánh: `feat/chat-status-indicator`, tách từ `dev` tại `5fc10c2`. Plan theo đề xuất mặc định của Q-01, Q-02 (người yêu cầu chấp nhận qua yêu cầu "implement task").

## Phân công

### S-01 — Gắn trạng thái header với `/api/health`

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: thêm hàm gọi health và query key; header `ChatView` suy ra trạng thái từ `loading` và kết quả health; lỗi mạng khi stream thì invalidate query health; phục vụ `AC-01`..`AC-06`.
- Phạm vi file được sửa: `frontend/src/api/` (file health mới hoặc bổ sung vào file sẵn có, export qua `index`), `frontend/src/ChatView.jsx` (chỉ phần header và nhánh xử lý lỗi stream), `frontend/src/styles/chat.css` hoặc `chat-motion.css` (màu chấm), test mới hoặc bổ sung `frontend/src/ChatView.test.jsx`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: diff, kết quả vitest, ảnh chụp bốn trạng thái.
- Người nhận: `claude-code` (coordinator).

## Hợp đồng dùng chung

- API dùng: `GET /api/health` → `{ status: "ok" | "degraded", database, database_type, embedding }`, HTTP 200 khi DB ổn; lỗi mạng hoặc 5xx coi là mất kết nối. Không sửa backend.
- File mã nguồn dùng chung và người sửa: `frontend/src/ChatView.jsx` cũng nằm trong phạm vi `2026-11-15-student-error-copy` và `2026-11-15-chat-header-new-chat-button`; `chat.css` nằm trong `2026-11-15-chat-header-dark-bg` và `2026-11-15-copy-btn-touch-keyboard`. Không sửa song song cùng file; coordinator xếp lượt.
- Lượt ghi năm file task: coordinator tổng hợp.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: `AC-01`..`AC-06`.
- Reviewer: `claude-code`; phạm vi: diff S-01.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: agent S-01.

## Thứ tự tích hợp và kiểm chứng

1. Chốt Q-01, Q-02.
2. S-01 triển khai.
3. Verifier chạy vitest; kiểm tra thủ công khi backend chạy, khi backend tắt và (nếu dựng được) khi embedding chưa cấu hình để có `degraded`.
4. Review, sửa, kiểm tra lại; coordinator đóng task.

## Rủi ro và điều chỉnh kế hoạch

- `ChatView` dùng chung nên trang admin cũng gọi health. Chấp nhận được; nếu muốn tắt ở admin thì thêm prop.
- Nginx production (FE-14) phải chuyển tiếp `/api/health`. Đã kiểm tra: `frontend/nginx.conf` có `location /api/` chuyển tiếp mọi route `/api/` còn lại, gồm `/api/health`.
- Ngoài phạm vi file ban đầu: sửa một regex trong `frontend/src/App.test.jsx` để chấp nhận `/api/health` là API công khai.

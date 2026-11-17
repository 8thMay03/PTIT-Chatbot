# Plan: 2026-11-15-student-error-copy

Nhánh: `feat/student-error-copy`, tách từ `dev` tại `f914187` (lúc soạn: `0fdd444`). Plan theo đề xuất mặc định của Q-01, Q-02 (đã chốt, xem `task.md`).

## Phân công

### S-01 — Tách câu chữ lỗi cho sinh viên và quản trị

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: thêm bộ ngữ cảnh lỗi cho sinh viên (bao gồm thay chuỗi lỗi mạng mặc định), truyền qua prop từ `App.jsx`; admin giữ ngữ cảnh hiện có; thêm nút "Thử lại" ở sidebar; chọn biểu tượng theo `kind` của `describeError`; phục vụ `AC-01`..`AC-05`.
- Phạm vi file được sửa: `frontend/src/ChatView.jsx` (`CHAT_ERROR_CONTEXT`, bubble lỗi), `frontend/src/App.jsx`, `frontend/src/admin/AdminShell.jsx` (chỉ truyền prop), `frontend/src/components/ConversationList.jsx`, có thể `frontend/src/api/errors.js` (thêm preset, không đổi mặc định), test (`ChatView.test.jsx`, `App.test.jsx` hoặc test mới cho `ConversationList`), CSS nút thử lại nếu cần.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: diff, kết quả vitest.
- Người nhận: `claude-code` (coordinator).

## Hợp đồng dùng chung

- Prop mới (đề xuất): `ChatView` và `ConversationList` nhận `errorContext` (object cùng khoá với options của `describeError`); không truyền thì dùng ngữ cảnh kỹ thuật hiện tại, để trang admin không phải sửa.
- Lỗi mạng: chuỗi detail do `api/client.js:266` tạo được `describeError` ưu tiên hơn `NETWORK_DETAIL`. Ngữ cảnh sinh viên phải thay được chuỗi này (ví dụ thêm option `networkDetail` ưu tiên hơn `error.detail` khi `code === "network"`).
- File mã nguồn dùng chung và người sửa: `ChatView.jsx`, `App.jsx`, `AdminShell.jsx` cũng nằm trong phạm vi task khác (xem `task.md`). Coordinator xếp lượt, không sửa song song.
- Lượt ghi năm file task: coordinator tổng hợp.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: `AC-01`..`AC-05`.
- Reviewer: `claude-code`; phạm vi: diff S-01.
- Hình thức review: `self_review` (một agent làm cả triển khai, kiểm chứng, review).
- Người xử lý nhận xét: agent S-01.

## Thứ tự tích hợp và kiểm chứng

1. Chốt Q-01, Q-02.
2. S-01 triển khai.
3. Verifier chạy vitest; kiểm tra thủ công `/chat` và `/admin` khi tắt backend.
4. Review, sửa, kiểm tra lại; coordinator đóng task.

## Rủi ro và điều chỉnh kế hoạch

- Đổi `api/errors.js` có thể ảnh hưởng mọi màn. Chỉ thêm option mới, không đổi giá trị mặc định nếu theo Q-01 mặc định.
- Điều chỉnh khi triển khai: `AdminShell.jsx` không cần sửa (không truyền `errorContext` thì giữ ngữ cảnh kỹ thuật); test dồn vào file mới `frontend/src/errorCopy.test.jsx` và `api/errors.test.js` thay vì `ChatView.test.jsx`/`App.test.jsx`; CSS nút thử lại ở `styles/layout.css`.

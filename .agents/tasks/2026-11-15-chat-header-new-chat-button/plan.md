# Plan: 2026-11-15-chat-header-new-chat-button

Nhánh dự kiến: `feat/chat-header-new-chat-button`, tách từ `dev` mới nhất (lúc soạn: `0fdd444`). Plan theo đề xuất mặc định của Q-01.

## Phân công

### S-01 — Nối nút header vào handler của trang cha

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: `ChatView` nhận prop `onNewChat`; nút header gọi `onNewChat ?? resetConversation`; đổi biểu tượng; `App.jsx` và `AdminShell.jsx` truyền `startNewChat`; phục vụ `AC-01`..`AC-05`.
- Phạm vi file được sửa: `frontend/src/ChatView.jsx` (props, nút header), `frontend/src/App.jsx`, `frontend/src/admin/AdminShell.jsx` (chỉ truyền prop), test (`App.test.jsx`, có thể `admin/AdminApp.test.jsx`).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: diff, kết quả vitest.
- Người nhận: `claude-code` (coordinator).

## Hợp đồng dùng chung

- Prop mới `onNewChat?: () => void` của `ChatView`. Không đổi API `ref` (`reset`, `loadConversation`) mà `App` và `AdminShell` đang dùng.
- File mã nguồn dùng chung và người sửa: `ChatView.jsx`, `App.jsx`, `AdminShell.jsx` cũng nằm trong phạm vi task khác (xem `task.md`). Coordinator xếp lượt; task này thay đổi ít dòng nên có thể làm trước.
- Lượt ghi năm file task: coordinator tổng hợp.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: `AC-01`..`AC-05`.
- Reviewer: `claude-code`; phạm vi: diff S-01.
- Hình thức review: `self_review` (một agent làm mọi vai trò).
- Người xử lý nhận xét: agent S-01.

## Thứ tự tích hợp và kiểm chứng

1. Chốt Q-01.
2. S-01 triển khai.
3. Verifier chạy vitest; nếu có backend thì kiểm tra thủ công ở `/chat` và `/admin`.
4. Review, sửa, kiểm tra lại; coordinator đóng task.

## Rủi ro và điều chỉnh kế hoạch

- `AdminShell.startNewChat` còn gọi `goTo("chat")`. Nút header chỉ hiện khi đang ở view chat nên không đổi gì với người dùng, nhưng kiểm tra không đẩy thêm mục vào lịch sử trình duyệt ngoài ý muốn.
  - Đã kiểm tra: `goTo` chỉ `setRoute`, không `pushState`; test `AdminApp` khẳng định `history.length` và hash `#chat` không đổi sau khi bấm nút header.

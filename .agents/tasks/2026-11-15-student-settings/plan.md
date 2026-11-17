# Plan: 2026-11-15-student-settings

## Phân công

### S-01 — Lối vào và khung hộp thoại

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-01`, `AC-02`.
- Phạm vi file được sửa: `frontend/src/App.jsx`, `frontend/src/components/UserMenu.jsx`, mới
  `frontend/src/student-settings/StudentSettingsDialog.jsx` (+ style), `frontend/src/App.test.jsx`.
- Phụ thuộc: S-02 (cần module tùy chọn để hiển thị giá trị); Q-02 cho vị trí menu tài khoản.
- Đầu ra/bàn giao: hộp thoại nhận `initialSection` (`general | account | data`), mở từ sidebar, menu tài khoản, hash.
- Người nhận: `claude-agent` (S-03, S-04).
- Ghi chú: bỏ hộp thoại "Giao diện" cũ trong `App.jsx`; `ThemePicker` vẫn dùng chung với tab Giao diện của admin.
- Blocker: hết — Q-02 (2026-11-17): chân thanh bên. Menu render qua portal (xem `implementation.md`).

### S-02 — Module tùy chọn và áp dụng

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: lưu/đọc tùy chọn và áp dụng cỡ chữ, phím gửi, panel suy luận; phục vụ `AC-03`.
- Phạm vi file được sửa: mới `frontend/src/lib/preferences.js` + `preferences.test.js`, `frontend/src/lib/keyboard.js`
  + test, `frontend/src/ChatView.jsx`, `frontend/src/ChatView.test.jsx`, `frontend/src/styles/tokens.css` hoặc
  `base.css`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: hook `usePreferences()` trả `{ fontScale, enterToSend, keepReasoningOpen, set }`; mặc định
  `{ "md", true, false }`; một khoá localStorage (ví dụ `ptit_chatbot_prefs`, JSON có `version`).
- Người nhận: `claude-agent` (S-01, S-03).
- Ghi chú:
  - Cỡ chữ đặt `data-font-scale` trên `<html>`; CSS đổi `--text-*` theo thuộc tính này.
  - Muốn tránh nháy cỡ chữ lúc tải trang thì phải sửa script inline trong `frontend/index.html`, kéo theo cập nhật hash
    CSP ở `frontend/nginx/page-headers.conf` (task `2026-11-07-fe14-nginx-production`). Nếu không muốn đổi CSP, áp dụng
    sau khi React mount và ghi rõ trong verification.
  - Phím gửi: thêm hàm, ví dụ `isSubmitKey(event, { enterToSend })`, giữ nguyên nhánh IME.

### S-03 — Nội dung nhóm Chung và Tài khoản

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-03` (giao diện), `AC-04`.
- Phạm vi file được sửa: `frontend/src/student-settings/*`, `frontend/src/components/ThemePicker.jsx` (nếu cần biến thể
  segmented), test component.
- Phụ thuộc: S-01, S-02.
- Đầu ra/bàn giao: nhóm Chung (4 điều khiển + xem trước + "Đã lưu trên thiết bị này"), nhóm Tài khoản.
- Người nhận: `claude-agent` (S-05).

### S-04 — Dữ liệu & lịch sử

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-05`.
- Phạm vi file được sửa:
  - Backend: `backend/app/api/routes.py` (`DELETE /conversations`), `backend/app/db/repositories.py`
    (`delete_conversations_for_owner`), test mới `backend/tests/test_conversation_bulk_delete.py`.
  - Frontend: `frontend/src/api/conversations.js`, mới `frontend/src/lib/exportConversations.js` + test,
    `frontend/src/student-settings/*`.
- Phụ thuộc: S-01; **Q-03** (người dùng).
- Đầu ra/bàn giao: endpoint + UI theo lựa chọn Q-03.
- Người nhận: `claude-agent` (S-05).
- Blocker: hết — Q-03 (2026-11-17): làm cả hai mục, không mục nào `cancelled`.
- Ghi chú: owner lấy từ `auth.get_client_session(...).owner_key`, giống `GET /conversations`. Route `DELETE
  /conversations` không được đè route `DELETE /conversations/{conversation_id}`.

### S-05 — Kiểm chứng và ảnh chụp

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-06` và bằng chứng cho `AC-01` … `AC-05`.
- Phạm vi file được sửa: `verification.md`.
- Phụ thuộc: S-01 … S-04 (hoặc S-04 `cancelled`).
- Đầu ra/bàn giao: kết quả lệnh, ảnh.
- Người nhận: reviewer.

## Hợp đồng dùng chung

- **`DELETE /api/conversations`** (S-04 cung cấp, đã làm theo Q-03): không body; xoá mọi hội thoại (và tin nhắn) của
  owner phiên hiện tại; trả `200 { "deleted": <int> }`; owner không có hội thoại thì trả `{ "deleted": 0 }`. Áp
  `client.apply(response)` như các route hội thoại khác.
- **Tùy chọn sinh viên** (S-02 cung cấp): khoá localStorage `ptit_chatbot_prefs` = `{ "version": 1, "fontScale":
  "sm"|"md"|"lg", "enterToSend": bool, "keepReasoningOpen": bool }`; giá trị lạ → mặc định.
- File mã nguồn dùng chung: `App.jsx`, `ChatView.jsx` — chỉ `claude-agent` sửa, tuần tự S-02 → S-01 → S-03.
- Lượt ghi năm file task: `claude-agent` ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: `AC-01` … `AC-06`.
- Reviewer: `claude-agent`; phạm vi: toàn bộ diff nhánh `feat/student-settings`.
- Hình thức review: `self_review` nếu chỉ một agent làm.
- Người xử lý nhận xét: `claude-agent`.

## Thứ tự tích hợp và kiểm chứng

1. Đọc lại trạng thái các task `2026-11-15-chat-header-*`; cập nhật `dev`; tách `feat/student-settings`.
2. S-02 → S-01 → S-03; S-04 khi có Q-03.
3. S-05: toàn bộ lệnh kiểm tra + ảnh.
4. Review, sửa, kiểm tra lại; coordinator đóng task, mở PR vào `dev`.

## Rủi ro và điều chỉnh kế hoạch

- Q-02 chọn chân sidebar → khối tài khoản chuyển chỗ, đụng đề xuất D-08 của nghiên cứu chat; có thể cần tách thành task
  riêng nếu kéo theo đổi màu sidebar.
- Cỡ chữ Lớn làm vỡ bố cục bong bóng/thẻ nguồn trên mobile → kiểm tra 390px, dùng token thay vì px cứng ở chỗ hỏng.
- Xuất lịch sử phía client với nhiều hội thoại tạo nhiều request → giới hạn đồng thời, hiện tiến độ; nếu chậm, đề xuất
  endpoint export ở task sau.

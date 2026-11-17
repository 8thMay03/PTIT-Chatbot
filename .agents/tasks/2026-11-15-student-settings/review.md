# Review: 2026-11-15-student-settings

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (một agent làm cả triển khai, kiểm chứng và review; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: nhánh `feat/student-settings`, commit `c491a2f` (tách từ `dev` `72a45b5`).
- Cập nhật lúc: `2026-11-17T22:14:33+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: `AC-01` … `AC-06`; `S-01` … `S-05`.
- File/thay đổi đã đọc: toàn bộ diff `dev..c491a2f` (backend route/repository/test; App, ChatView, UserMenu, Modal,
  ThemePicker, StudentSettingsDialog, preferences, keyboard, exportConversations, API, CSS và test).
- Bằng chứng kiểm chứng: `verification.md` V-01 … V-06, `evidence/ui-checks.json`, ảnh trong `evidence/`.
- Điểm đánh giá: bundle trang chat không kéo mã admin; IME khi đổi phím gửi; storage bị chặn; quyền sở hữu khi xoá
  toàn bộ; a11y hộp thoại và menu; cỡ chữ Lớn trên mobile.

## Đánh giá

- Bundle: `check:bundle` đạt, chat 89.80 kB gzip; hộp thoại import `Modal`, `api`, `auth/session` (đã có trong chunk
  chat), không import màn admin.
- IME: `isSubmitKey` dùng chung `isImeComposing` cho cả hai chế độ; có test Enter và Ctrl/Cmd+Enter chốt chữ.
- Storage: mọi đọc/ghi `ptit_chatbot_prefs` bọc try/catch; test ép `getItem`/`setItem` ném lỗi. Hộp thoại báo không
  lưu được thay vì báo đã lưu.
- Quyền sở hữu: owner lấy giống `GET /conversations`; test chứng minh không xoá của owner khác và cookie admin không
  đổi owner. Owner rỗng trả 0. Route mới nằm trong `PUBLIC_API_ROUTES` có chủ đích; test quét route admin xanh.
  Cookie phiên/tài khoản `SameSite=Lax`/`Strict` nên request DELETE từ trang khác không mang cookie — cùng mức như
  `DELETE /conversations/{id}` đã có.
- A11y: `Modal` giữ focus trap/Esc/trả focus; radiogroup có roving tabindex, switch có `aria-labelledby` +
  `aria-describedby`; menu tài khoản đủ `aria-haspopup`/`aria-expanded`/`aria-controls`, Esc/Tab trả focus về chip.
  Xác nhận xoá trong thẻ thay vì modal lồng (tránh Esc đóng cả hộp thoại ngoài) — hợp lý với `Modal` hiện tại.
- Bố cục: số đo 390px cỡ Lớn không tràn; `md` giữ cỡ cũ.

## Nhận xét

### R-01 — Cỡ chữ áp dụng sau khi React mount

- Vị trí: `frontend/src/lib/preferences.js` (`usePreferences` gọi `applyFontScale` trong effect).
- Vấn đề: người chọn Nhỏ/Lớn có thể thấy cỡ Vừa trong khoảnh khắc lúc tải `/chat`.
- Tác động: nháy hình nhỏ, không sai chức năng.
- Mức độ: `low`; bắt buộc sửa: không.
- Trạng thái: `deferred` — sửa triệt để cần script inline trong `frontend/index.html` và cập nhật hash CSP ở
  `frontend/nginx/page-headers.conf` (ghi chú sẵn trong `plan.md` S-02); làm ở task riêng nếu thấy phiền.

### R-02 — Đăng xuất từ hộp thoại: focus không có chỗ trả về

- Vị trí: `StudentSettingsDialog.jsx` `AccountSection` → App `handleLoggedOut` + đóng hộp thoại.
- Vấn đề: chip tài khoản (nút đã mở menu/hộp thoại) bị thay bằng link Đăng nhập sau khi đăng xuất, nên `Modal` không
  trả focus được; focus về `body`.
- Tác động: người dùng bàn phím phải Tab lại từ đầu trang sau khi đăng xuất.
- Mức độ: `low`; bắt buộc sửa: không.
- Trạng thái: `deferred` — có thể focus vào link Đăng nhập hoặc `#main-content` sau khi đăng xuất; cùng hành vi với
  nút đăng xuất trên header trước đây (nút cũng biến mất).

### R-03 — Xuất lịch sử phía client tốn 1 + N request

- Vị trí: `frontend/src/lib/exportConversations.js`.
- Vấn đề: mỗi hội thoại một request chi tiết (tối đa 4 song song); lịch sử rất dài sẽ chậm.
- Tác động: chỉ khi bấm "Tải xuống"; nút hiện tiến độ `x/y`, huỷ khi đóng hộp thoại.
- Mức độ: `low`; bắt buộc sửa: không.
- Trạng thái: `deferred` — đề xuất endpoint export phía server nếu có phản hồi chậm (đã ghi trong rủi ro `plan.md`).

### R-04 — Ảnh chụp dùng API giả lập

- Vị trí: `evidence/`.
- Vấn đề: `/api/**` giả lập trong Chromium; ảnh chứng minh bố cục/tương tác, không chứng minh dữ liệu thật.
- Mức độ: `low`; bắt buộc sửa: không.
- Trạng thái: `deferred` — cùng cách làm các task Settings trước; backend đã có test riêng cho endpoint mới.

### R-05 — `:has()` cho z-index của backdrop

- Vị trí: `frontend/src/styles/student-settings.css` (`.modal-backdrop:has(> .student-settings)`).
- Vấn đề: trình duyệt không hỗ trợ `:has()` (Firefox < 121, Safari < 15.4) giữ z-index 40, nên trên mobile mở Cài
  đặt từ drawer thì drawer (45) nằm trên hộp thoại.
- Tác động: chỉ trình duyệt cũ, chỉ khi mở từ drawer mobile; vẫn đóng được bằng Esc/nút đóng sau khi đóng drawer.
- Mức độ: `low`; bắt buộc sửa: không.
- Trạng thái: `deferred` — nếu cần hỗ trợ trình duyệt cũ, thêm prop `backdropClassName` cho `Modal`.

## Lịch sử các vòng review

- Vòng 1 (`c491a2f`, `2026-11-17T22:14:33+07:00`): self_review; 5 nhận xét `low`, không bắt buộc, đều `deferred`.
  Hai lỗi phát hiện khi chụp ảnh (drawer đè hộp thoại trên mobile; menu bị cắt khi thanh bên thu gọn) đã sửa trước
  commit và có trong verification.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01 … R-05 (`low`).
- Phần chưa review / giới hạn: chưa kiểm trên thiết bị thật và trình đọc màn hình thật.
- Bước tiếp theo: người dùng review PR [#73](https://github.com/8thMay03/PTIT-Chatbot/pull/73).

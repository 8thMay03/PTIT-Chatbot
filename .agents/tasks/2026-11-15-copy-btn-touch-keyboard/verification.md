# Verification: 2026-11-15-copy-btn-touch-keyboard

- Verifier: `claude-code`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: nhánh `feat/copy-btn-touch-keyboard` @ `3e8922a`.
- Môi trường: Windows 11, Vite dev server `localhost:5173` (backend `localhost:8000` chạy cho `/api/health`, `/api/auth/me`), Playwright Python + Chromium headless. Chrome extension không kết nối nên không dùng DevTools device mode; chưa thử điện thoại thật.

## Cách kiểm tra chung (V-01..V-03)

Script `evidence/verify_actions.py` mock `GET /api/conversations` (một hội thoại) và `GET /api/conversations/c1` (4 tin: user, assistant, user, assistant `interrupted: true`), mở `/chat`, bấm hội thoại rồi đo `getComputedStyle(...).opacity` sau khi transition xong. Kết quả thô: `evidence/results.json`. Thứ tự phần tử `.bubble-actions`: `[user, assistant, user, assistant is-pinned]`.

Lệnh (từ thư mục gốc repo, khi dev server đang chạy):

```bash
python -I -X utf8 .agents/tasks/2026-11-15-copy-btn-touch-keyboard/evidence/verify_actions.py <thư mục ảnh>
```

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T21:02:31+07:00`.
- Loại: kiểm tra trình duyệt tự động (Playwright).
- Thư mục chạy: gốc repo.
- Lệnh / thao tác: desktop 1366×800; focus phần tử ngay trước nút "Sao chép" của câu trả lời thứ nhất rồi nhấn `Tab`.
- Kỳ vọng: nút hiện và có vòng focus.
- Kết quả thực tế: phần tử focus là `.copy-btn` trong `.message-row.assistant`, khớp `:focus-visible`, outline `solid 2px rgb(151, 38, 53)`; opacity `.bubble-actions` = `["0","1","0","1"]` (câu trả lời đang focus hiện, các tin khác vẫn ẩn).
- Trạng thái: `passed`.
- Bằng chứng: `evidence/results.json` (`keyboard_*`), `evidence/desktop-keyboard-focus.png`.

### V-02 — AC-02

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T21:02:31+07:00`.
- Loại: kiểm tra trình duyệt tự động (Playwright).
- Thư mục chạy: gốc repo.
- Lệnh / thao tác: context `devices["Pixel 7"]` (isMobile, hasTouch); mở sidebar bằng `.mobile-menu-btn`, mở hội thoại, đo opacity; mở lại sidebar và chụp.
- Kỳ vọng: nút "Sao chép", nút đổi tên và nút xóa luôn hiện.
- Kết quả thực tế: `matchMedia('(hover: none)')` = `true`; opacity `.bubble-actions` = `["1","1","1","1"]`; `.conv-actions` = `["1"]` mà không có hover hay focus.
- Trạng thái: `passed`.
- Bằng chứng: `evidence/results.json` (`touch_*`), `evidence/touch-chat.png`, `evidence/touch-sidebar.png`.
- Giới hạn: giả lập trong Chromium, chưa thử trên điện thoại thật.

### V-03 — AC-03

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T21:02:31+07:00`.
- Loại: kiểm tra trình duyệt tự động (Playwright).
- Thư mục chạy: gốc repo.
- Lệnh / thao tác: desktop 1366×800 (`(hover: none)` = `false`); bỏ focus, đưa chuột ra góc màn hình, đo; rê vào câu trả lời thứ nhất, đo; rê vào hội thoại trong sidebar, đo.
- Kỳ vọng: hover như cũ; tin bị dừng luôn hiện nhãn.
- Kết quả thực tế: lúc nghỉ `.bubble-actions` = `["0","0","0","1"]` (chỉ tin `is-pinned` hiện), `.conv-actions` = `["0"]`; khi rê câu trả lời thứ nhất = `["0","1","0","1"]`; khi rê hội thoại `.conv-actions` = `["1"]`.
- Trạng thái: `passed`.
- Bằng chứng: `evidence/results.json` (`desktop_*`), `evidence/desktop-idle.png`, `evidence/desktop-hover.png`.

### V-04 — AC-04

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T21:02+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm run build`; bổ sung `npx vitest run`.
- Kỳ vọng: pass.
- Kết quả thực tế: build xong (`✓ built in 2.20s`); vitest 35 file / 243 test pass.
- Trạng thái: `passed`.
- Bằng chứng: output lệnh trong phiên làm việc.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy đầu của script bị timeout vì route mock khớp nhầm module Vite `/src/api/conversations.js`; sửa điều kiện route thành tiền tố `http://localhost:5173/api/conversations`. Không liên quan mã sản phẩm.
- Chưa kiểm tra trên điện thoại thật và trình đọc màn hình (thay đổi chỉ là `opacity`, không đổi cây truy cập).

## Kết luận

- Tiêu chí đã đạt: `AC-01`, `AC-02`, `AC-03`, `AC-04`.
- Tiêu chí chưa đạt/chưa xác minh: không có (giới hạn: chưa thử thiết bị thật).
- Đề xuất: review và mở PR.

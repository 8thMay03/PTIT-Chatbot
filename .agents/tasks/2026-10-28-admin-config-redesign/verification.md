# Verification: 2026-10-28-admin-config-redesign

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: nhánh `feat/admin-config-redesign`, working tree trước commit (cùng nội dung commit).
- Môi trường: Linux, Node + `npm ci`, Vite 5 dev server, Chromium (Playwright) với `/api/*` giả lập
  (`admin/session` đã đăng nhập, `config` trả cấu hình mặc định).

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-agent / `2026-10-28T23:45:00+07:00`.
- Loại: kiểm tra thủ công bằng Playwright.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: mở `/admin#settings/config` ở 1024×800, bấm mục 4 của mục lục.
- Kỳ vọng: vùng cuộn tới nhóm "Mô hình sinh câu trả lời", mục 4 được đánh dấu active.
- Kết quả thực tế: `scrollTop` = 1100, mục active "4. Mô hình sinh câu trả lời — Temp 0.00 · 30s"; ảnh chụp cho
  thấy hàng chip dính sát dưới thanh tiêu đề, không che tiêu đề nhóm.
- Trạng thái: `passed`.
- Bằng chứng: ảnh chụp trong phiên (không commit).

### V-02 — AC-02, AC-03, AC-04

- Người thực hiện / thời gian: claude-agent / `2026-10-28T23:45:00+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run src/ConfigView`.
- Kỳ vọng: 3 test mới + 4 test cache hiện có đạt.
- Kết quả thực tế: `Test Files 2 passed (2)`, `Tests 7 passed (7)`.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra vitest.

### V-03 — AC-03 (Ctrl+S)

- Người thực hiện / thời gian: claude-agent / `2026-10-28T23:45:00+07:00`.
- Loại: kiểm tra thủ công bằng Playwright.
- Lệnh / thao tác: đổi Temperature thành 0.5, nhấn Ctrl+S; chuyển sang tab Mô hình, nhấn Ctrl+S.
- Kỳ vọng: một request `PUT /api/config` sau lần nhấn đầu; không có request mới ở tab Mô hình.
- Kết quả thực tế: số PUT = 1 rồi vẫn = 1. Lưu ý: sau lần lưu form không còn thay đổi, nên lần nhấn thứ hai
  chỉ xác nhận không lưu thừa, chưa chứng minh riêng nhánh `[hidden]`.
- Trạng thái: `passed`.
- Bằng chứng: log script Playwright.

### V-04 — AC-05

- Người thực hiện / thời gian: claude-agent / `2026-10-28T23:44:00+07:00`.
- Loại: kiểm tra thủ công (ảnh chụp).
- Lệnh / thao tác: chụp 1440×1000 sáng/tối, 1024×800, 390×844; có và không có thay đổi chưa lưu.
- Kỳ vọng: không tràn ngang, chữ không bị cắt, thanh lưu không che nút, màu đúng ở dark mode.
- Kết quả thực tế: đạt; ở 390px thanh lưu xuống hai hàng (trạng thái / hai nút chia đôi).
- Trạng thái: `passed`.
- Bằng chứng: ảnh chụp trong phiên (không commit).

### V-05 — AC-06

- Người thực hiện / thời gian: claude-agent / `2026-10-28T23:46:00+07:00`.
- Loại: test tự động + build.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run`; `npm run build`; `BUNDLE_REPORT=1 npx vite build && npm run check:bundle`.
- Kỳ vọng: tất cả đạt.
- Kết quả thực tế: `Test Files 16 passed (16)`, `Tests 87 passed (87)`; build thành công;
  "Tổng gzip JS ban đầu: 128.41 kB (mốc phải nhỏ hơn: 156.79 kB) — check:bundle đạt."
- Trạng thái: `passed`.
- Bằng chứng: đầu ra lệnh.

### V-06 — AC-06 (lớp CSS dùng chung)

- Loại: review mã.
- Lệnh / thao tác: grep từng lớp CSS cũ trong `src/**/*.jsx` trước khi xoá.
- Kết quả thực tế: các lớp đã xoá không còn JSX nào dùng; lớp tab Mô hình dùng vẫn giữ.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chụp đầu ở 1024px: hàng chip mục lục dính cách mép trên 24px (sticky tính từ padding của vùng cuộn) làm
  lộ nội dung phía trên. Đã sửa bằng `top: -24px` / `-20px`, chụp lại đạt (V-01).
- Chưa chạy với backend thật và trên Firefox/Safari.

## Kết luận

- Tiêu chí đã đạt: AC-01…AC-06.
- Tiêu chí chưa đạt/chưa xác minh: không có.
- Đề xuất: bàn giao người dùng xem lại giao diện.

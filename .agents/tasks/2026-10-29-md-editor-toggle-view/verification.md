# Verification: 2026-10-29-md-editor-toggle-view

- Verifier: `claude-agent`.
- Bản kiểm chứng: nhánh `feat/md-editor-toggle-view`, working tree trước commit S-01.
- Cập nhật lúc: `2026-10-29T22:20:59+07:00`.

## Kết quả

### V-01 — Test đơn vị trình sửa (AC-01, AC-02, AC-03)

- Lệnh: `npx vitest run src/components/MarkdownEditorView.test.jsx` (trong `frontend/`).
- Kết quả: `passed` — 6 test. Mới: chuyển chế độ bằng nút (tiêu đề, bản render hiện nội dung chưa lưu, textarea giữ
  nguyên phần tử và chỉ `hidden`), nhớ cột `original`/`markdown`, đổi giá trị cũ `["rendered"]` → `["markdown"]`.

### V-02 — Toàn bộ test, build, bundle (AC-04)

- Lệnh: `npm test`, `npm run build`, `npm run check:bundle`.
- Kết quả: `passed` — 20 file, 161 test; build xong; tổng gzip 82.45 kB (mốc FE-06 128.41 kB, không vượt).
- Ghi chú: lần chạy đầu 3 file (`LoginPage`, `RegisterPage`, `LandingPage`) và build lỗi vì thiếu
  `@fontsource/readex-pro` trong `node_modules`; sau `npm install` đạt.

### V-03 — Trình duyệt thật (AC-01, AC-02, AC-04)

- Cách làm: harness Vite tạm (đã xoá) render `MarkdownEditorView`, Playwright (Chromium 1234) chặn `/api/*` trả
  Markdown 243 dòng; cuộn ô sửa tới 50 %, bấm "Xem bản render", rồi "Sửa Markdown".
- Kết quả: `passed` — ở 1280 sáng, 1280 tối, 390 sáng: tỉ lệ cuộn bản render 0.50, quay lại ô sửa 0.50; không cuộn
  ngang. Ảnh chụp cho thấy hai cột (Bản gốc | Markdown), tiêu đề và nút đổi theo chế độ, bảng/tiêu đề render đúng.

### V-04 — Lịch sử hoàn tác (AC-02)

- Cách làm: test V-01 khẳng định textarea là cùng một phần tử trước/sau khi xem bản render (không remount).
- Kết quả: `passed`.

## Kết luận

- Mọi `AC-*` đạt.

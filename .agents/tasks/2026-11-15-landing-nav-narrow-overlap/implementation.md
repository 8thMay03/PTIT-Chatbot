# Implementation: 2026-11-15-landing-nav-narrow-overlap

## Tổng quan triển khai

Nhánh `feat/landing-nav-narrow-overlap` (tách từ `dev` tại `11b7ac4`, trùng `origin/dev` lúc tách). Người yêu cầu giao việc bằng lệnh "implement this task". Working tree lúc tách có sẵn hai thay đổi không thuộc task này: file PDF trong `data/` bị xoá và thư mục task `2026-11-15-student-error-copy` chưa track. Cả hai được giữ nguyên, không commit.

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-11-15T21:32:49+07:00`.
- Trạng thái: `in_review`.
- Nguyên nhân đo được trên bản cũ (Playwright Chromium, chi tiết ở `verification.md`): 40/120 phép kiểm tra chồng chữ. Lỗi không chỉ có ở 480–520px mà còn ở 320px, 640px và 1100px. Khi đã đăng nhập với tên dài, lỗi xuất hiện cả ở 768–1440px. Bề rộng tự nhiên đo được: tên thương hiệu 141px (117px khi <480px), "Trợ lý học vụ" 98px, ba liên kết 409px, cụm nút khách 290px (343px từ 900px), cụm nút đã đăng nhập 469px (531px). Thanh nav còn có trạng thái "viên thuốc" khi cuộn (`landing-motion.css`: `padding-inline: 12px` + viền), làm phần nội dung hẹp thêm 26px. Ảnh chụp ban đầu của task không thấy trạng thái này.
- Đã làm:
  - `frontend/src/styles/landing.css`:
    - `.lp-brand-name`: thêm `min-width: 0; overflow: hidden; text-overflow: ellipsis`. Đây là lưới an toàn: thiếu chỗ thì cắt "…", không tràn sang phần tử bên cạnh. Quy tắc này dùng chung với header `/login`, `/register` và footer, đã kiểm tra không bị cắt ở đó.
    - `.lp-nav-divider`, `.lp-nav-tagline`: thêm `flex-shrink: 0` để vạch chia không bị bóp mất và dòng phụ không đè lên tên.
    - Khi đã đăng nhập (`.lp-nav-inner.is-signed-in`): ẩn vạch chia và "Trợ lý học vụ"; tên người dùng thế vào chỗ đó.
    - Dưới 480px: ẩn mũi tên trong nút của nav (khối `max-width: 479px` có sẵn).
    - Dưới 520px và đã đăng nhập: ẩn chữ thương hiệu, chỉ giữ biểu tượng. Link vẫn có `aria-label="PTIT Chatbot — Trang chủ"`.
    - Nút đổi giao diện và "Đăng nhập": hiện từ 600px (trước là 480px).
    - Vạch chia, dòng phụ và tên người dùng: hiện từ 768px (trước là 640px). Ẩn trong khoảng 1100–1319px, lúc ba liên kết vừa hiện; hiện lại từ 1320px.
  - `frontend/src/landing/LandingPage.jsx`: thêm modifier `is-signed-in` vào `.lp-nav-inner` khi `session.isAuthenticated`. Không đổi cấu trúc khác.
- File thay đổi: 2 file trên; commit: xem `git log dev..feat/landing-nav-narrow-overlap`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác:
  - D-01: các ngưỡng được tính theo bề rộng đo thật, có chừa 26px cho trạng thái cuộn, để tên thương hiệu không phải cắt từ 340px trở lên. Dưới 340px, khách ở trạng thái cuộn bị cắt tên ("PTIT Cha…"); AC-02 cho phép cách này.
  - D-02: khi đã đăng nhập, ẩn "Trợ lý học vụ" ở mọi bề rộng. Ở 1280px, ba liên kết, dòng phụ, tên người dùng (tối đa 180px) và nút "Vào trò chuyện" không vừa cùng lúc, nên phải bỏ một phần. Tên người dùng hữu ích hơn dòng trang trí. Người yêu cầu có thể đổi lựa chọn này.
  - D-03: không thêm menu hamburger (ngoài phạm vi). Ba liên kết vẫn hiện từ 1100px như cũ.
  - Không đổi API, không đổi `.lp-btn` hay `.theme-toggle` dùng chung.
- Kiểm tra đã chạy: `npm test` (35 file, 244 test pass), `npm run build` pass. Đo bố cục tự động: 192/192 phép kiểm tra đạt ở 12 bề rộng của AC-01. Quét thêm 291 bề rộng (bước 4px, từ 320 đến 1440px) × 3 trạng thái phiên × 2 trạng thái nav: 0 lỗi. Xem `verification.md`.
- Còn lại/blocker: chưa kiểm tra bằng DevTools device mode trên trình duyệt có giao diện như `plan.md` đề ra. Đã thay bằng Playwright Chromium với viewport giả lập (lý do ở `verification.md`).

## Trao đổi giữa agents

Chưa có thông báo.

## Bàn giao

- `2026-11-15T21:32:49+07:00` — claude-code → người yêu cầu: S-01 xong trên nhánh `feat/landing-nav-narrow-overlap` (chưa push). Việc cần làm tiếp: xem trực quan bộ ảnh trong `evidence/`, quyết định D-02, rồi push và mở PR vào `dev`.
- `2026-11-15T21:49:10+07:00` — claude-code: đã push nhánh và mở PR #69 (https://github.com/8thMay03/PTIT-Chatbot/pull/69) vào `dev` theo yêu cầu người yêu cầu.

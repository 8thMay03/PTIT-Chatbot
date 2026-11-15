# Verification: 2026-11-15-chat-header-dark-bg

- Verifier: `claude-code`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `feat/chat-header-dark-bg` (nền `0fdd444` + diff S-01 ở `tokens.css`, `chat.css`), trùng nội dung commit triển khai.
- Môi trường: Windows 11, Node v24.14.0, `vite build` + `vite preview` (cổng 4179), Chrome headless điều khiển qua CDP (khung 1440×900, DPR 1).

Cách đo (V-01, V-02): script CDP đặt `prefers-color-scheme` bằng `Emulation.setEmulatedMedia`, đặt `localStorage.ptit_chatbot_theme`, nạp lại `/chat`, rồi trong trang lấy `getComputedStyle` của `.chat-header`, ghép các lớp nền bán trong suốt từ gốc xuống phần tử để ra nền hiệu dụng và tính tỉ lệ tương phản WCAG 2.x giữa màu chữ và nền hiệu dụng. Kết quả thô: `evidence/contrast-results.json`. Phép ghép bỏ qua `backdrop-filter` và nội dung cuộn dưới header (trạng thái welcome không có gì nằm dưới header).

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-code, `2026-11-15T18:22:00+07:00`.
- Loại: kiểm tra trên trình duyệt (tự động hoá bằng CDP), thay cho thao tác tay trong DevTools.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: (a) `prefers-color-scheme: dark`, theme `system` (không có `data-theme`); (b) `prefers-color-scheme: light`, theme `dark` (`data-theme="dark"`).
- Kỳ vọng: nền header tối; tương phản tối thiểu 4.5:1 ở cả (a) và (b).
- Kết quả thực tế, (a) và (b) giống hệt nhau:
  - Nền header computed `rgba(20, 23, 28, 0.72)`, nền hiệu dụng `rgb(18, 21, 25)`.
  - Chữ "Sẵn sàng hỗ trợ" `rgb(232, 234, 238)`: **15.22:1**.
  - Nút "Đăng nhập" (chữ trắng trên nền brand riêng của nút, `rgb(197, 61, 82)`): **5.04:1**.
  - Nút icon "Bắt đầu cuộc trò chuyện mới" `rgb(151, 160, 173)` trên `rgb(20, 23, 28)`: **6.80:1**.
- Trạng thái: `passed`.
- Bằng chứng: `evidence/header-system-dark.png`, `evidence/header-manual-dark.png`, `evidence/contrast-results.json`.

### V-02 — AC-02

- Người thực hiện / thời gian: claude-code, `2026-11-15T18:22:00+07:00`.
- Loại: kiểm tra trên trình duyệt + so giá trị computed.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: theme `light`, `prefers-color-scheme: light`.
- Kỳ vọng: không khác biệt nhìn thấy được.
- Kết quả thực tế: nền header computed `rgba(255, 255, 255, 0.72)`, trùng từng giá trị với màu viết cứng trước khi sửa; `backdrop-filter: blur(10px)` giữ nguyên. Vì giá trị computed giống hệt nên ảnh render trước/sau giống nhau; không chụp ảnh "trước" riêng. Tương phản: chữ trạng thái 17.51:1, "Đăng nhập" 7.94:1, nút icon 5.68:1.
- Trạng thái: `passed`.
- Bằng chứng: `evidence/header-light.png`, `evidence/contrast-results.json`.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-code, `2026-11-15T18:20:00+07:00`.
- Loại: review mã.
- Thư mục chạy: repo.
- Lệnh / thao tác: `git diff -- frontend/`; tìm `rgba(255, 255, 255` trong `frontend/src/styles/chat.css`.
- Kỳ vọng: nền header dùng token; token có ở khối sáng và cả hai khối tối.
- Kết quả thực tế: `.chat-header` dùng `background: var(--surface-glass)`; không còn `rgba(255, 255, 255` trong quy tắc `.chat-header` (các kết quả còn lại ở dòng ~250, ~944, ~969 thuộc quy tắc khác). `--surface-glass` có ở `:root`, khối `@media (prefers-color-scheme: dark)` và `:root[data-theme="dark"]`.
- Trạng thái: `passed`.
- Bằng chứng: diff trong commit triển khai (4 dòng thêm, 1 dòng xoá ở 2 file).

### V-04 — AC-04

- Người thực hiện / thời gian: claude-code, `2026-11-15T18:21:00+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm test`, `npm run build`.
- Kỳ vọng: cả hai pass.
- Kết quả thực tế: `npm test`: Test Files 34 passed (34), Tests 225 passed (225). `npm run build`: `built in 2.17s`, không lỗi.
- Trạng thái: `passed`.
- Bằng chứng: output terminal của phiên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Chưa kiểm tra riêng khung chat trong `/admin` (cần đăng nhập admin); dùng chung `ChatView` và cùng quy tắc `.chat-header` nên kết quả như `/chat`.
- Chưa đo trạng thái đã đăng nhập (`.user-name`) và trạng thái có tin nhắn cuộn dưới header; màu chữ đều lấy từ token theo theme.
- Chỉ chụp ở rộng 1440px; nền header không phụ thuộc breakpoint (`responsive.css` chỉ đổi `padding`).

## Kết luận

- Tiêu chí đã đạt: `AC-01`, `AC-02`, `AC-03`, `AC-04`.
- Tiêu chí chưa đạt/chưa xác minh: không có (giới hạn phạm vi đo ghi ở trên).
- Đề xuất: merge sau khi người yêu cầu duyệt PR.

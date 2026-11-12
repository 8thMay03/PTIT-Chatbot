# Verification: 2026-11-12-chunk-highlight-mapping

- Verifier: `claude-code`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree trên `feat/chunk-highlight-mapping` (nền `20e1b92`).
- Môi trường: Windows 11, Node 24, jsdom/vitest từ `frontend/node_modules`; DB Postgres local (container `ptit_chatbot_postgres`).

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-code / `2026-11-12T23:58:00+07:00`.
- Loại: đánh giá trên dữ liệu thật (script ngoài repo, trong scratchpad của phiên).
- Thao tác: export `parsed_text` và 1017 đoạn của tài liệu `e0997dd2…` (Sổ tay sinh viên D26) từ DB; render bằng `renderMarkdownHtml` trong jsdom; chạy thuật toán cũ và mới cho từng đoạn. Bản mới chạy qua `createChunkLocator` với danh sách trang 20, 50, 100 đoạn như giao diện.
- Chỉ số: "không định vị" = không có vùng (bản cũ: rơi về đoán theo tỷ lệ); "lùi" = khối đầu của đoạn i nằm trước của đoạn i−1; độ phủ = tỷ lệ mảnh của đoạn có trong chữ vùng đánh dấu; độ chính xác = tỷ lệ chữ trong vùng thuộc về đoạn.
- Kết quả thực tế:

  | Thuật toán | Không định vị | Lùi | Độ phủ TB | Độ chính xác TB |
  |---|---|---|---|---|
  | Cũ | 136 | 124 | 0.627 | 0.956 |
  | Mới (trang 20/50/100) | 0 | 0 | 0.977 | 0.999 |

  Soi tay các đoạn có độ phủ < 0.8 (ví dụ #487, #446): vùng đúng; độ phủ thấp do đoạn ghi số khoản nội dòng ("1. …; 2. …") còn bản render là danh sách đánh số tự động — số không có trong `textContent`.
- Trạng thái: `passed`.

### V-02 — AC-02

- Lệnh: `npx vitest run src/lib/chunkLocator.test.js` (thư mục `frontend/`).
- Kết quả thực tế: 7 test passed.
- Trạng thái: `passed`.

### V-03 — AC-03

- Lệnh: `npx vitest run`; `npx vite build` (thư mục `frontend/`).
- Kết quả thực tế: 34 file test, 225 test passed; `built in 2.13s`.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Kiểm tra thủ công trên trình duyệt: `not_run` (extension Claude in Chrome không kết nối).

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-02, AC-03.
- Chưa xác minh: hành vi trên trình duyệt thật (cuộn, độ trễ lần trỏ đầu).

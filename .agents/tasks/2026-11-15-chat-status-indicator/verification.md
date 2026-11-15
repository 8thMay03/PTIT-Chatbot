# Verification: 2026-11-15-chat-status-indicator

- Verifier: `claude-code` (cũng là người triển khai).
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: nhánh `feat/chat-status-indicator` (working tree trên `5fc10c2`, nội dung giống commit S-01).
- Môi trường: Windows 11, Node, Vitest 3.2.7 (jsdom), Vite dev server, Chrome headless (`--headless=new`), backend FastAPI thật đang chạy ở `localhost:8000` (PostgreSQL, embedding `ready`).
- Cập nhật lúc: `2026-11-15T19:10:00+07:00`.

Cách dựng trạng thái lỗi mà không tắt backend thật của người dùng: chạy Vite thứ hai ở cổng 5174 với `VITE_PROXY_TARGET=http://localhost:8998`, trỏ tới một server Node giả trả `/api/health` → `{ status: "degraded", ... }`. Tắt server giả thì proxy Vite trả HTTP 500, giống khi backend tắt sau proxy. Ảnh chụp lưu ở `%TEMP%\chat-status-shots\` (không đưa vào repo).

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T19:08+07:00`.
- Loại: test tự động và kiểm tra thủ công (headless Chrome).
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác:
  - Vitest `trạng thái máy chủ trên header > lỗi mạng khi focus lại…` và `> 503 khi focus lại…`: health ok → đổi backend giả sang `TypeError`/503 → giả lập focus lại cửa sổ (`focusManager`) → kiểm tra header; rồi đổi lại ok → focus lại → về sẵn sàng.
  - Thủ công: tắt server giả (`curl http://localhost:5174/api/health` → `500`), chụp `http://localhost:5174/chat` (1280×720 và 390×760).
- Kỳ vọng: header hiện trạng thái mất kết nối, màu khác xanh, không còn "Sẵn sàng hỗ trợ".
- Kết quả thực tế: test pass. Ảnh `offline.png`: chấm đỏ + "Mất kết nối máy chủ". Chu kỳ 60 giây được kiểm tra qua cấu hình (`refetchInterval: 60_000`), chưa quan sát bằng đồng hồ trên trình duyệt.
- Trạng thái: `passed`.
- Bằng chứng: output vitest bên dưới; `%TEMP%\chat-status-shots\offline.png`, `offline-mobile.png`.

### V-02 — AC-02

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T19:08+07:00`.
- Loại: test tự động và kiểm tra thủ công.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: vitest `degraded: nhãn hạn chế, chấm cảnh báo (AC-02)`; chụp `http://localhost:5174/chat` khi server giả trả `degraded`.
- Kỳ vọng: header hiện trạng thái hạn chế.
- Kết quả thực tế: test pass; ảnh `degraded.png`: chấm vàng + "Đang hạn chế, câu trả lời có thể chậm hoặc lỗi". Ở 390px (`degraded-mobile.png`) nhãn xuống hai dòng, chấm giữ nguyên kích thước.
- Trạng thái: `passed`.
- Bằng chứng: `%TEMP%\chat-status-shots\degraded.png`, `degraded-mobile.png`.

### V-03 — AC-03

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T19:08+07:00`.
- Loại: test tự động và kiểm tra thủ công.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: vitest `ok: Sẵn sàng hỗ trợ…` và `đang stream: Đang trả lời... rồi về trạng thái máy chủ`; chụp `http://localhost:5173/chat` với backend thật.
- Kỳ vọng: "Sẵn sàng hỗ trợ" khi rảnh, "Đang trả lời..." khi stream.
- Kết quả thực tế: test pass; ảnh `ok.png`: chấm xanh + "Sẵn sàng hỗ trợ". Chưa gửi câu hỏi thật trên trình duyệt (không có extension Chrome để thao tác); trạng thái stream chỉ có bằng chứng từ vitest.
- Trạng thái: `passed`.
- Bằng chứng: `%TEMP%\chat-status-shots\ok.png`, `ok-mobile.png`.

### V-04 — AC-04

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T19:07+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: vitest `stream lỗi mạng: kiểm tra lại health ngay…` (chat/stream ném `TypeError`, đếm lần gọi health sau khi gửi) và `lỗi 4xx của chat không làm kiểm tra lại health` (429 → 0 lần gọi).
- Kỳ vọng: health được gọi lại ngay sau lỗi mạng; không gọi với 4xx.
- Kết quả thực tế: pass; sau lỗi mạng health được gọi 1 lần và header chuyển "Mất kết nối máy chủ".
- Trạng thái: `passed`.
- Bằng chứng: output vitest.

### V-05 — AC-05

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T19:08+07:00`.
- Loại: review mã và test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: vitest kiểm tra `.chat-header .title` có `role="status"` và `aria-live="polite"`; các test khác kiểm tra nhãn chữ khác nhau giữa năm trạng thái.
- Kỳ vọng: thay đổi trạng thái được đọc lên; nhãn chữ khác nhau giữa các trạng thái.
- Kết quả thực tế: pass. Chưa nghe thực tế bằng Narrator.
- Trạng thái: `passed` (phần Narrator `not_run`).
- Bằng chứng: output vitest; `ChatView.jsx` phần header.

### V-06 — AC-06

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T19:07+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm test`, `npm run build`, `npm run check:bundle`.
- Kỳ vọng: cả hai pass.
- Kết quả thực tế: `Test Files 34 passed (34)`, `Tests 237 passed (237)`; `✓ built in 2.08s`; `Tổng gzip: 83.92 kB (mốc FE-06, không vượt: 128.41 kB)`, `check:bundle đạt.`
- Trạng thái: `passed`.
- Bằng chứng: output lệnh trong phiên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy `npm test` đầu: `App.test.jsx > không có lối vào Dataset/Settings, chỉ gọi API công khai` thất bại vì header gọi `/api/health`, không khớp regex `conversations|auth/me`. Đã thêm `health` vào regex (route công khai); chạy lại 237/237 pass.
- Ảnh chụp 390px bị cắt mép phải ở cả trạng thái `ok` (nhãn ngắn), nên không do thay đổi này gây ra; có thể do headless Chrome áp độ rộng cửa sổ tối thiểu. Chưa kiểm tra trên thiết bị thật.
- Chưa xác minh: Narrator; chu kỳ 60 giây đo trên trình duyệt; tắt backend thật (dùng proxy tới server giả thay thế).

## Kết luận

- Tiêu chí đã đạt: `AC-01`..`AC-06`.
- Tiêu chí chưa đạt/chưa xác minh: không có tiêu chí bắt buộc nào chưa đạt; các phần thủ công còn thiếu ghi ở trên.
- Đề xuất: người yêu cầu review và merge PR #65.

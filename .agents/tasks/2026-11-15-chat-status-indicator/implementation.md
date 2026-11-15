# Implementation: 2026-11-15-chat-status-indicator

## Tổng quan triển khai

Nhánh `feat/chat-status-indicator` (tách từ `dev` tại `5fc10c2`). Header chat lấy trạng thái từ `GET /api/health` qua TanStack Query (khi mount, khi cửa sổ focus lại, chu kỳ 60 giây khi tab mở) và từ `loading`; stream lỗi mạng/5xx thì invalidate query health để kiểm tra lại ngay. Theo đề xuất mặc định Q-01, Q-02.

## Nhật ký theo nhiệm vụ

### S-01 — `claude-code`

- Cập nhật lúc: `2026-11-15T19:10:00+07:00`.
- Trạng thái: `done`.
- Đã làm:
  - `frontend/src/api/health.js` (mới): `get({ signal })` gọi `request("health", { timeout: 10_000 })`; timeout ngắn để báo mất kết nối sớm. Export `healthApi` qua `api/index.js`; thêm `queryKeys.health = ["health"]`.
  - `frontend/src/ChatView.jsx`:
    - `useQuery` health: `staleTime: 0`, `refetchInterval: 60_000` (TanStack mặc định không chạy khi tab ẩn), `refetchOnWindowFocus: true`; `retry` theo client chung (`0`).
    - `HEADER_STATUS` + `headerStatusKey(loading, health)`: `busy` "Đang trả lời..." → `offline` "Mất kết nối máy chủ" (lần kiểm tra gần nhất lỗi, kể cả còn dữ liệu cũ) → `checking` "Đang kiểm tra kết nối..." (chưa có kết quả đầu tiên) → `ready` "Sẵn sàng hỗ trợ" (`status: "ok"`) / `degraded` "Đang hạn chế, câu trả lời có thể chậm hoặc lỗi" (mọi giá trị khác `ok`).
    - Vùng `.title` có `role="status"` `aria-live="polite"`; chấm `aria-hidden="true"`.
    - `isConnectivityError`: `TypeError` (stream bị cắt giữa chừng), `ApiError` mã `network`/`timeout` hoặc `status >= 500` → `queryClient.invalidateQueries({ queryKey: queryKeys.health })` trong nhánh `catch` của `sendMessage`. Lỗi 4xx (429/422/413) không kích hoạt.
  - `frontend/src/styles/chat.css`: `.status-dot.is-checking` (`--text-muted`), `.is-degraded` (`--warning`), `.is-offline` (`--danger`); `flex-shrink: 0` cho chấm, `min-width: 0` cho `.title` để nhãn dài xuống dòng trên màn hẹp mà chấm không bị bóp.
  - `frontend/src/ChatView.test.jsx`: render trong `QueryClientProvider` riêng mỗi test (`renderChat`); backend giả có route `health` (mặc định `ok`), `healthCalls` đếm riêng nên `fetchMock` của các test cũ không đổi ý nghĩa; reset `focusManager` sau mỗi test. Thêm 7 test trong "trạng thái máy chủ trên header".
  - `frontend/src/App.test.jsx`: thêm `health` vào regex "chỉ gọi API công khai" (`/api/health` nằm trong `PUBLIC_API_ROUTES` của backend). File này ngoài phạm vi ghi trong plan; chỉ sửa một regex vì thay đổi của S-01 làm test cũ thất bại.
- File thay đổi: `frontend/src/api/health.js`, `frontend/src/api/index.js`, `frontend/src/api/queryClient.js`, `frontend/src/ChatView.jsx`, `frontend/src/styles/chat.css`, `frontend/src/ChatView.test.jsx`, `frontend/src/App.test.jsx`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác:
  - Thêm trạng thái thứ năm `checking` cho lúc chưa có kết quả health đầu tiên, để header không khẳng định "Sẵn sàng" trước khi biết. Thường chỉ hiện vài trăm ms.
  - `ChatView` giờ bắt buộc nằm trong `QueryClientProvider` (cả `/chat` và `/admin` đều đã có từ `main.jsx`). Test nào render `ChatView` trực tiếp phải bọc provider.
  - Mọi lỗi của health (kể cả 4xx như 404 do sai `VITE_API_BASE_URL`) đều hiện "Mất kết nối máy chủ", vì đều có nghĩa là frontend không tới được API.
  - Nginx: `location /api/` đã chuyển tiếp `/api/health`; không cần sửa.
- Kiểm tra đã chạy: xem `verification.md` (vitest 237/237, build, check:bundle, ảnh chụp headless Chrome ba trạng thái).
- Còn lại/blocker: không có.

## Trao đổi giữa agents

Chưa có thông báo (một agent kiêm các vai trò).

## Bàn giao

- Nhiệm vụ: S-01 hoàn tất.
- Nhánh/commit: `feat/chat-status-indicator`, commit trên `5fc10c2` (xem `git log`).
- Kiểm tra: `npm test` 34 file / 237 test pass; `npm run build` pass; `npm run check:bundle` đạt (gzip 83.92 kB / mốc 128.41 kB).
- Chưa làm: chưa push/PR; chưa nghe bằng Narrator; chưa quan sát chu kỳ 60 giây thật trên trình duyệt (chỉ kiểm tra cấu hình và luồng focus).
- Người nhận: người yêu cầu `8thMay03`, để duyệt và quyết định push/PR.

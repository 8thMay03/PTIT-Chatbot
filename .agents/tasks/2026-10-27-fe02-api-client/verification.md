# Verification: 2026-10-27-fe02-api-client

- Trạng thái tổng: `passed`
- Bản được kiểm: working tree nhánh `feat/api-client-state` tại thời điểm
  `2026-10-27T07:41:08+07:00` (chưa commit).
- Môi trường: Windows, Node `v24.14.0`, npm `11.21.1`, Vite `5.4.21`,
  `@tanstack/react-query@5.105.0`.

## AC-01 — Không còn `fetch(` trong component/view

- Trạng thái: `passed`
- Lệnh:
  `rg -n "\bfetch\(" frontend/src --glob "!**/*.test.*"`
- Kết quả: chỉ còn một dòng `frontend/src/api/client.js:208` bên trong `request()`.
  NDJSON được đọc trong `frontend/src/api/chat.js` (`streamChat`), view không tự parse stream.

## AC-02 — Cache `/config` dùng chung giữa hai tab

- Trạng thái: `passed`
- Lệnh: `npx vitest run src/ConfigView.cache.test.jsx`
- Kết quả: `1 file, 4 tests passed`.
  - `lưu trạng thái reranker ở tab Cấu hình thì tab Mô hình cập nhật ngay`: bật/tắt reranker ở
    `ConfigView`, bấm lưu, `ModelsView` đổi từ `Đang bật` sang `Đang tắt` mà không tải lại trang.
  - `nhận cấu hình mới từ tab khác nhưng giữ trường đang sửa dở`: cập nhật cache `/config` từ bên ngoài,
    `ConfigView` nhận `reranker.enabled = false` nhưng giữ `temperature = 0.7` đang sửa.
  - `reset đồng bộ form ngay cả khi máy chủ trả đúng dữ liệu đã cache`: Temperature về 0, badge "Có thay
    đổi chưa lưu" biến mất dù response giống cache; sửa tiếp 0.7 rồi cập nhật từ tab Mô hình vẫn giữ 0.7.
  - `lưu chỉ API key thì xoá khoá khỏi input và tắt trạng thái chưa lưu`: input rỗng, nút Lưu bị vô hiệu.
- Bổ sung: `npx vitest run src/lib/configDraft.test.js` — `2 tests passed`.
- Bổ sung: `npx vitest run src/api/errors.test.js` — `2 tests passed`, gồm giữ detail backend cho 5xx.
- Ghi chú: hai tab dùng cùng key `["config"]`; mọi lần lưu đều `setQueryData` rồi `invalidateQueries`.

## AC-03 — Timeout 30 giây báo lỗi rõ ràng

- Trạng thái: `passed`
- Lệnh: `npx vitest run src/api/client.test.js`
- Kết quả: test `báo ApiError timeout khi request vượt quá thời gian chờ` đạt; lỗi có
  `status = 0`, `code = "timeout"`, `detail` chứa `30 giây` và hướng dẫn kiểm tra máy chủ.
- Ghi chú: query mặc định `retry: 0`, nên màn hình nhận lỗi ngay sau 30 giây thay vì chờ thêm lượt retry.

## AC-04 — Unit test `request()`

- Trạng thái: `passed`
- Lệnh: `npm test`
- Kết quả: `7 test files passed`, `54 tests passed`, gồm 5 test của `src/api/client.test.js`:
  lỗi mạng, 4xx kèm `detail`, 5xx, timeout 30 giây, caller abort.

## AC-05 — Phân loại lỗi tập trung

- Trạng thái: `passed`
- Lệnh:
  `rg -n "instanceof TypeError" frontend/src`
  `rg -n "describeError|errorMessage" frontend/src --glob "*.jsx"`
- Kết quả: `instanceof TypeError` chỉ còn trong `frontend/src/api/client.js` và
  `frontend/src/api/errors.js`; các view dùng `describeError` cho màn lỗi và `errorMessage` cho toast.
  `apiError` cũ trong `lib/format.js` đã được xoá.

## AC-06 — Build và test

- Trạng thái: `passed`
- Lệnh: `npm test`
- Kết quả: `8 test files passed`, `58 tests passed`, thời gian ~1,98 giây.
- Lệnh: `npm run build`
- Kết quả: thành công; `index-2_o06J30.js` 468,90 kB (gzip 155,03 kB), `index-JefO1ocb.css`
  81,90 kB (gzip 14,73 kB), `docx-preview` 174,03 kB (gzip 51,04 kB).

## Ghi chú kiểm tra chưa chạy

- Chưa chạy backend thật/API tích hợp; các test dùng mock `fetch` và component test.
- Chưa đo thời gian upload/parse PDF thật; timeout 5 phút là cấu hình có chủ đích.

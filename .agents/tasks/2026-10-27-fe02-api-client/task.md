# Task: FE-02 — Lớp API client dùng chung và quản lý trạng thái server

- ID: `2026-10-27-fe02-api-client`
- Trạng thái: `done`
- Coordinator / người thực hiện: `opencode-agent`
- Reviewer: vòng 1 `opencode-agent` (`self_review`); vòng 2–3 `cursor-reviewer` (độc lập)
- Người yêu cầu: người dùng (phiếu FE-02)
- Tạo lúc: `2026-10-27T00:33:25+07:00`
- Cập nhật lúc: `2026-10-27T07:54:21+07:00`

## Yêu cầu và kết quả mong muốn

`frontend/src/api.js` hiện chỉ export `API_BASE_URL`; 22 lời gọi `fetch` nằm rải rác trong view/component,
mỗi chỗ tự xử lý lỗi, không có timeout, không huỷ khi rời màn. `ConfigView` và `ModelsView` đọc `/config`
riêng nên lưu ở tab này không cập nhật tab kia; `App.refreshDocCount` gọi `/documents` rồi bỏ kết quả.
Mục tiêu: một module `api/` có `request()` chuẩn hoá lỗi/mã trạng thái/thời gian chờ, các hàm theo domain,
TanStack Query cho cache `/config` + danh sách tài liệu/hội thoại, và một chỗ phân loại lỗi dùng chung.

## Phạm vi

- Bao gồm:
  - `frontend/src/api/` (mới): `client.js`, `errors.js`, `chat.js`, `documents.js`, `conversations.js`,
    `config.js`, `queryClient.js`, `index.js`.
  - `frontend/src/main.jsx`: bọc `QueryClientProvider`.
  - `frontend/src/App.jsx`: bỏ `refreshDocCount`, bỏ prop `onChanged`, invalidate hội thoại sau khi lưu.
  - `frontend/src/ChatView.jsx`, `ConfigView.jsx`, `ModelsView.jsx`, `DatasetView.jsx`, `DocumentView.jsx`,
    `components/ConversationList.jsx`, `components/MarkdownEditorView.jsx`,
    `components/ParserSelectionModal.jsx`, `components/OriginalDocumentViewer.jsx`.
  - `frontend/src/lib/configDraft.js` + test: gộp giá trị server vào bản nháp đang sửa.
  - `frontend/package.json`, `frontend/package-lock.json`: thêm `@tanstack/react-query`.
  - Test `frontend/src/api/client.test.js`.
- Ngoài phạm vi: thay đổi backend, đổi giao diện/CSS ngoài phần trạng thái lỗi, thêm optimistic update
  phức tạp cho tài liệu.
- Ràng buộc: React 18, Vite 5, Node 24; giữ nguyên hợp đồng API backend; request thường mặc định timeout
  30 giây; request tải/parse tài liệu được phép lâu hơn; luồng stream chat vẫn nhận NDJSON như cũ.

## Tiêu chí nghiệm thu

- [x] AC-01: Không còn component/view nào gọi `fetch(` trực tiếp; phần đọc NDJSON nằm trong `api/chat.js`.
- [x] AC-02: Lưu ở tab Mô hình thì tab Cấu hình RAG nhận giá trị mới qua cache chung và ngược lại, không
  cần tải lại trang; không xoá trường người dùng đang sửa dở ở tab kia.
- [x] AC-03: Request quá thời gian mặc định 30 giây trả `ApiError` mã `timeout` với thông báo rõ ràng.
- [x] AC-04: `request()` có unit test cho lỗi mạng, 4xx kèm `detail`, 5xx và timeout.
- [x] AC-05: Phân loại lỗi tập trung trong `api/errors.js`, dùng cho cả toast và màn lỗi.
- [x] AC-06: `npm test` và `npm run build` thành công.

## Tài liệu và phụ thuộc

- Phiếu FE-02 do người dùng cung cấp trong phiên làm việc.
- Không phụ thuộc task khác; nên làm trước FE-06, FE-07, FE-11, FE-13.
- Hợp đồng backend: `backend/app/api/routes.py`, `backend/app/api/schemas.py`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã tạo module `api/`, chuyển toàn bộ view/component sang domain API và TanStack Query, thêm
  cache `/config` dùng chung; xử lý vòng review R-05 … R-08. `npm test` 58 test đạt, `npm run build`
  thành công.
- Blocker: không.
- Bước tiếp theo: đã commit thay đổi trên nhánh `feat/api-client-state`; chờ merge vào `dev`.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-27T00:33:25+07:00` — `opencode-agent`: tạo task từ phiếu FE-02, giữ backend ngoài phạm vi.
- `2026-10-27T00:46:58+07:00` — `opencode-agent`: hoàn tất triển khai, kiểm chứng và tự review; chuyển
  trạng thái `done`.
- `2026-10-27T07:41:08+07:00` — `opencode-agent`: xử lý R-05 (reset/save đồng bộ form trực tiếp),
  R-06 (reset draft sau lưu API key), R-07 (huỷ request mở hội thoại), R-08 (giữ detail 5xx); kiểm chứng
  lại và giữ trạng thái `done`.
- `2026-10-27T07:45:42+07:00` — `cursor-reviewer`: xác nhận vòng 3, `approved`.
- `2026-10-27T07:53:22+07:00` — `opencode-agent`: commit thay đổi trên nhánh `feat/api-client-state`
  (`4e4d297`).

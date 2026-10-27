# Implementation: 2026-10-27-fe02-api-client

## Bàn giao

- Nhánh: `feat/api-client-state` (tách từ `dev` tại `fbeca75`, `dev` đã cập nhật từ `origin/dev`).
- Trạng thái: đã triển khai, kiểm chứng và tự review; chưa commit (working tree của nhánh).
- Phụ thuộc mới: `@tanstack/react-query@5.105.0`.

## Nhật ký

### 2026-10-27T00:33:25+07:00 — `opencode-agent`

- Tạo task, tạo nhánh `feat/api-client-state`, thêm `@tanstack/react-query` vào frontend.
- Chưa có thay đổi mã nguồn tính năng.

### 2026-10-27T00:45:32+07:00 — `opencode-agent`

- Tạo module `frontend/src/api/`:
  - `client.js`: `request()` dùng base URL, query params, JSON/FormData, timeout mặc định 30 giây bằng
    `AbortController`, timeout riêng cho upload/parse/chunk (5 phút), `responseType` cho JSON/text/blob/
    arrayBuffer/stream/response.
  - `errors.js`: `ApiError{status, detail, code}`, `isAbortError`, `describeError`, `errorMessage`.
  - `chat.js`: đọc NDJSON `/chat/stream` bằng async generator; view chỉ xử lý event.
  - `documents.js`, `conversations.js`, `config.js`: bọc toàn bộ endpoint backend.
  - `queryClient.js`/`index.js`: `QueryClient`, `queryKeys`, export namespace.
- Xoá `frontend/src/api.js`; mọi import `./api` giờ trỏ vào thư mục module.
- Bọc `App` bằng `QueryClientProvider` trong `main.jsx`; query mặc định `retry: 0`, `staleTime: 15s`,
  không refetch khi focus cửa sổ.
- `ConfigView` và `ModelsView` dùng chung query `["config"]`; sau PUT/POST reset đều
  `setQueryData` + `invalidateQueries(["config"])`.
  - `ConfigView` gộp giá trị server qua `mergeConfigDraft`, chỉ nhận trường người dùng chưa sửa.
  - `ModelsView` giữ bản nháp LLM/reranker khi các trường liên quan không đổi.
- `DatasetView`, `ConversationList`, `DocumentView` dùng TanStack Query; các thao tác ghi invalidate
  tiền tố `["documents"]` hoặc key hội thoại. Bỏ `refreshDocCount`, `onChanged`, `reloadToken`,
  `conversationsToken`.
- Các màn còn lại (`ChatView`, `MarkdownEditorView`, `ParserSelectionModal`, `OriginalDocumentViewer`)
  dùng domain API và `signal` để huỷ khi unmount/đổi tài liệu.
- Gom phân loại lỗi về `api/errors.js`; toast dùng `errorMessage`, màn lỗi dùng `describeError`.
- Thêm test:
  - `frontend/src/api/client.test.js`: mạng, 4xx có `detail`, 5xx, timeout 30 giây, caller abort.
  - `frontend/src/lib/configDraft.test.js`: giữ bản nháp, nhận giá trị mới.
  - `frontend/src/ConfigView.cache.test.jsx`: lưu reranker ở tab Cấu hình cập nhật tab Mô hình; cache
    cập nhật từ ngoài vẫn giữ trường đang sửa.
- Sửa trong lúc kiểm chứng: mảng rỗng fallback của danh sách tài liệu được ổn định bằng hằng số để
  tránh vòng effect; `request()` không gửi `method: "GET"` thừa để tương thích test double hiện có;
  đọc `detail` từ response lỗi không có content-type.

### 2026-10-27T00:46:58+07:00 — `opencode-agent`

- Chạy lại toàn bộ `npm test` (54 test đạt) và `npm run build` sau lần chỉnh cuối; cập nhật
  `verification.md`/`review.md` theo bản mới nhất.

### 2026-10-27T07:41:08+07:00 — `opencode-agent`

- Sửa R-05: bỏ `forceSyncRef`; sau save/reset gọi `applyServerConfig(response)` để đặt thẳng `values` và
  `savedSnapshot`, kể cả khi TanStack Query giữ nguyên object cache. Thêm test reset về mặc định khi
  server trả đúng dữ liệu đã cache, và test sửa tiếp sau reset không bị lần cập nhật sau xoá.
- Sửa R-06: sau khi lưu LLM, dựng lại draft từ `next.llm` để API key vừa lưu không còn trong input và
  trạng thái "chưa lưu" tắt. Thêm test lưu chỉ API key.
- Sửa R-07: `ChatView.loadConversation` nhận `AbortController`, huỷ khi mở hội thoại khác, reset hoặc
  unmount.
- Sửa R-08: `describeError` giữ chi tiết backend cho lỗi 5xx; thêm `api/errors.test.js`.
- Chạy lại `npm test`: 8 file, 58 test đạt; `npm run build` thành công.

## Quyết định

- Timeout 30 giây chỉ áp dụng cho API thường; upload/parse/chunk dùng 5 phút vì PDF lớn có thể lâu.
- Stream chat chỉ giới hạn thời gian tới lúc nhận header; sau đó người dùng dừng bằng nút có sẵn.
- Query mặc định không retry để lỗi timeout hiện đúng sau 30 giây, không kéo dài thêm một lượt.
- `ConfigView` không ghi đè trường đang sửa dở khi tab khác lưu; trường không sửa nhận giá trị mới ngay.

## Chưa xong / rủi ro

- Chưa có test tích hợp chạy backend thật; kiểm chứng dùng mock fetch và test component.
- Upload/parse cực lớn vượt 5 phút vẫn báo timeout; ngoài phạm vi tối ưu hàng đợi.
- Không commit/merge; người dùng review diff trên nhánh `feat/api-client-state`.

## Người nhận và bước tiếp theo

- Người nhận: người dùng/coordinator.
- Bước tiếp theo: review diff, chạy lại `npm test`/`npm run build` nếu cần, commit và merge khi đồng ý.

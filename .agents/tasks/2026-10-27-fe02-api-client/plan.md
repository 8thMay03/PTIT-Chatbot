# Plan: 2026-10-27-fe02-api-client

## Phân công

### S-01 — Lõi `request()` và phân loại lỗi

- Agent: `opencode-agent`
- Trạng thái: `done`
- Mục tiêu: `api/client.js` với base URL, JSON, query, FormData, timeout 30 giây bằng `AbortController`,
  `ApiError{status, detail, code}`; `api/errors.js` có `describeError`/`errorMessage` dùng chung.
- Phạm vi file: `frontend/src/api/client.js`, `frontend/src/api/errors.js`, `frontend/src/api/index.js`.
- Phụ thuộc: không.
- Đầu ra/bàn giao: `request(path, options)`, `ApiError`, `isAbortError`, `describeError`, `errorMessage`.
- Người nhận: `opencode-agent`.

### S-02 — Hàm theo domain và query client

- Agent: `opencode-agent`
- Trạng thái: `done`
- Mục tiêu: bọc toàn bộ endpoint backend trong `chat`, `documents`, `conversations`, `config`; thêm
  `queryKeys`/`queryClient`; đưa đọc NDJSON vào `api/chat.js`.
- Phạm vi file: rest of `frontend/src/api/`; `frontend/src/main.jsx`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: không còn URL API rải rác ngoài module `api/`.
- Người nhận: `opencode-agent`.

### S-03 — Chuyển view/component sang API + TanStack Query

- Agent: `opencode-agent`
- Trạng thái: `done`
- Mục tiêu: `ConfigView`/`ModelsView` dùng chung query `["config"]` và invalidate sau khi lưu; danh sách
  tài liệu/hội thoại dùng query; bỏ `refreshDocCount`; lỗi toast/màn lỗi dùng `describeError`.
- Phạm vi file: `App.jsx`, `ChatView.jsx`, `ConfigView.jsx`, `ModelsView.jsx`, `DatasetView.jsx`,
  `DocumentView.jsx`, `components/ConversationList.jsx`, `components/MarkdownEditorView.jsx`,
  `components/ParserSelectionModal.jsx`, `components/OriginalDocumentViewer.jsx`, `lib/configDraft.js`.
- Phụ thuộc: S-02.
- Đầu ra/bàn giao: AC-01, AC-02, AC-05.
- Người nhận: `opencode-agent`.

### S-04 — Test và kiểm chứng

- Agent: `opencode-agent`
- Trạng thái: `done`
- Mục tiêu: test `request()` cho lỗi mạng/4xx/5xx/timeout; test gộp bản nháp cấu hình; chạy `npm test`,
  `npm run build`.
- Phạm vi file: `frontend/src/api/client.test.js`, `frontend/src/lib/configDraft.test.js`.
- Phụ thuộc: S-01, S-03.
- Đầu ra/bàn giao: AC-03, AC-04, AC-06.
- Người nhận: `opencode-agent`.

## Hợp đồng dùng chung

- `request(path, { method, query, body, headers, signal, timeout, responseType })`
  - `path` tương đối với `API_BASE_URL`; `body` object tự chuyển JSON, `FormData` giữ nguyên.
  - `timeout` mặc định `30000` ms; hết giờ ném `ApiError` với `code === "timeout"`.
  - Lỗi HTTP ném `ApiError` có `status` và `detail` lấy từ `detail`/`message` của backend.
  - `responseType`: `json` (mặc định), `text`, `blob`, `arrayBuffer`, `stream`, `response`, `none`.
  - Huỷ bởi `signal` của caller ném `AbortError` gốc để màn hình bỏ qua.
- `describeError(error, options)` trả `{ kind, title, detail }`; `errorMessage(error, fallback)` trả chuỗi
  ngắn cho toast. Không nơi nào tự phân loại `TypeError`/mã HTTP riêng.
- Query key: `["config"]`, `["documents", "list"]`, `["documents", "detail", id]`, `["conversations", "list"]`.
  Mọi thay đổi tài liệu invalidate tiền tố `["documents"]`; lưu cấu hình `setQueryData(["config"])` rồi
  invalidate `["config"]`.
- File dùng chung chỉ `opencode-agent` sửa trong task này; không có agent khác chạy song song.

## Phân công kiểm chứng và review

- Verifier: `opencode-agent`; phạm vi: AC-01 … AC-06, `npm test`, `npm run build`, grep `fetch(`.
- Reviewer: `opencode-agent`; phạm vi: diff module `api/`, các view, test, package.
- Hình thức review: `self_review` (chỉ có một agent trong phiên).
- Người xử lý nhận xét: `opencode-agent`; reviewer tự xác nhận sau khi sửa.

## Thực tế tích hợp và kiểm chứng

1. S-01 → S-02 → S-03 tuần tự vì dùng chung `index.js` và cách đặt query key.
2. S-04 viết sau khi chốt chữ ký `request` và luồng `streamChat`.
3. Kiểm chứng chạy trên working tree của nhánh `feat/api-client-state` (tách từ `dev` tại `fbeca75`).
4. Bổ sung test component `ConfigView.cache.test.jsx` để chứng minh cache `/config` cập nhật giữa hai tab
   và không xoá trường đang sửa; không chỉ dựa vào test hàm `mergeConfigDraft`.

## Rủi ro và điều chỉnh kế hoạch

- Rủi ro: `ConfigView` đang có bản nháp chưa lưu, cache `/config` đổi từ tab khác. Giảm thiểu:
  `mergeConfigDraft` chỉ nhận trường không bị sửa cục bộ; lưu/khôi phục thì ép đồng bộ theo server.
- Rủi ro: timeout 30 giây không phù hợp upload/parse PDF lớn. Giảm thiểu: các hàm upload/parse/chunk
  truyền timeout 5 phút; stream chat chỉ giới hạn thời gian tới khi nhận header.
- Rủi ro: đổi `DocumentView` sang query làm mất dữ liệu trang cũ khi đổi trang. Chấp nhận: vẫn hiện
  skeleton như hành vi trước; dữ liệu được cache theo `(documentId, offset, limit)`.

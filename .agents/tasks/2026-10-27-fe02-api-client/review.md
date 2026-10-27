# Review: 2026-10-27-fe02-api-client

- Trạng thái: `approved` (vòng 3, `2026-10-27T07:45:42+07:00`, reviewer `cursor-reviewer`)
- Vòng 2 (`changes_requested`) và vòng 1 (`approved`, `self_review`) được giữ bên dưới làm lịch sử.

## Vòng 3 — xác nhận sửa R-05 … R-08

- Reviewer: `cursor-reviewer`
- Bản được review: working tree nhánh `feat/api-client-state` (chưa commit, nền `fbeca75`) sau lượt
  sửa `2026-10-27T07:41:08+07:00` của `opencode-agent`, kiểm tại `2026-10-27T07:45:42+07:00`.
- Đã đọc: `ConfigView.jsx` (`applyServerConfig`, handler save/reset, effect gộp bản nháp),
  `ModelsView.jsx` (`LlmSection.handleSave`, `RerankerSection`), `ChatView.jsx`
  (`loadConversation`, `conversationAbortRef`), `api/errors.js`, `api/errors.test.js`,
  `ConfigView.cache.test.jsx`.
- Chạy lại: `rg -n "\bfetch\(" src --glob "!**/*.test.*"` chỉ còn `api/client.js:208`; `npm test`
  8 file / 58 test đạt; `npm run build` thành công (`index-2_o06J30.js` 468,90 kB). Khớp
  `verification.md`.

### Xác nhận từng nhận xét

- R-05 — `resolved`. `forceSyncRef` đã bỏ; `applyServerConfig(next)` đặt `values`, `savedSnapshot`,
  `previousServerRef` trước `setQueryData`, nên đồng bộ không phụ thuộc tham chiếu cache. Khi cache
  đổi, effect gộp nhận `current == previous == server` nên không ghi đè gì thêm. Test mới
  `reset đồng bộ form ngay cả khi máy chủ trả đúng dữ liệu đã cache` phủ đúng hai kịch bản đã tái lập ở
  vòng 2 (reset khi dữ liệu không đổi; sửa tiếp rồi nhận cập nhật từ ngoài vẫn giữ bản nháp).
- R-06 — `resolved`. `LlmSection.handleSave` dựng lại draft từ `next.llm` sau khi lưu; `initialKey` vẫn
  giữ để lưu từ tab Cấu hình RAG không xoá bản nháp. `RerankerSection` không cần sửa vì `initialKey`
  của nó phủ đủ trường mà `rerankerDraftFromConfig` dùng. Test `lưu chỉ API key…` (has_key
  `false` → `true`) xác nhận input rỗng, nút Lưu bị vô hiệu.
- R-07 — `resolved`. Mỗi lượt mở hội thoại có `AbortController` riêng, huỷ lượt trước, khi reset và khi
  unmount; `AbortError` được bỏ qua; `finally` chỉ xoá ref nếu vẫn là controller hiện tại.
- R-08 — `resolved`. Nhánh 5xx nối `detail` backend vào `serverDetail`, bỏ qua chuỗi mặc định do client
  tạo (`Máy chủ gặp lỗi (mã …)`); trang HTML của proxy đã bị `responseToApiError` lọc từ trước.

### Ghi chú quy trình (không chặn)

- Lượt sửa ghi thẳng vào `review.md`: thêm R-05 … R-08 với trạng thái `resolved`, kết luận `approved`
  dưới mục vòng 1, và đổi mốc thời gian bản được review của vòng 1 từ `00:46:58` sang `07:41:08`. Theo
  `.agents/README.md`, người triển khai ghi cách sửa trong `implementation.md` và reviewer chuyển
  nhận xét sang `resolved`. Vòng này giữ nguyên các mục đó làm lịch sử phản hồi của người triển khai,
  khôi phục mốc vòng 1 về `00:46:58` và chỉ coi xác nhận ở vòng 3 là có hiệu lực.
- `verification.md` mục AC-04 vẫn ghi `7 test files`/`54 tests`; số đúng sau lượt sửa là 8/58 (đã ghi
  ở AC-06). Verifier nên cập nhật cho nhất quán.
- `task.md` vẫn ghi coordinator kiêm reviewer `self_review`; nên ghi thêm review độc lập vòng 2–3.

### Kết luận vòng 3

`approved` trên bản working tree nêu trên. Không còn nhận xét bắt buộc chưa xử lý; R-03, R-04 vẫn
`deferred` theo vòng 1.

---

## Vòng 2 — review độc lập

- Reviewer: `cursor-reviewer` (agent khác với người triển khai)
- Bản được review: working tree nhánh `feat/api-client-state` (chưa commit, nền `fbeca75`) tại
  `2026-10-27T00:55:11+07:00`; cùng nội dung với bản vòng 1.
- Đã đọc: toàn bộ `frontend/src/api/`, diff mọi view/component trong phạm vi, `lib/configDraft.js`,
  các test mới; đối chiếu `backend/app/api/routes.py` cho mã trạng thái và hình dạng response.
- Chạy lại kiểm chứng: `rg -n "\bfetch\(" src --glob "!**/*.test.*"` chỉ còn `api/client.js:208`;
  `npm test` 7 file / 54 test đạt; `npm run build` thành công (bundle khớp số liệu trong
  `verification.md`). Bằng chứng AC-01, AC-03, AC-04, AC-06 tái lập được.
- Probe tạm thời (`src/zz_review_probe.test.jsx`, đã xoá sau khi chạy) để kiểm R-05.

### R-05 — `ConfigView` không đồng bộ khi máy chủ trả dữ liệu không đổi; cờ ép đồng bộ bị kẹt

- Vị trí: `frontend/src/ConfigView.jsx` — `handleResetConfig`, `handleSaveAll`, effect theo
  `serverValues`, `forceSyncRef`.
- Vấn đề: hai handler đặt `forceSyncRef.current = true` rồi `setQueryData(next)` và trông vào effect
  `[serverValues]` để ghi đè bản nháp. TanStack Query dùng structural sharing: nếu `next` bằng sâu
  với cache thì `configQuery.data` giữ nguyên tham chiếu, `serverValues` không đổi, effect không chạy.
  - Khôi phục mặc định khi cấu hình đã là mặc định (hoặc lưu khi bản nháp chỉ khác kiểu, vd. ô
    nhập trả chuỗi `"0"` so với số `0`): toast báo thành công nhưng form vẫn giữ giá trị đang sửa và
    nhãn "Có thay đổi chưa lưu" vẫn hiện.
  - `forceSyncRef` kẹt ở `true`; lần cập nhật cache kế tiếp từ tab Mô hình sẽ ghi đè toàn bộ bản
    nháp đang sửa — trái AC-02 ("không xoá trường người dùng đang sửa dở").
- Tái lập: probe render `ConfigView` với `/config` và `/config/reset` trả cùng dữ liệu, sửa
  Temperature thành `0.7`, bấm Mặc định → Khôi phục: Temperature vẫn `0.7`, nhãn chưa lưu vẫn hiện.
  Sau đó `setQueryData` từ ngoài (đổi `reranker.enabled`): Temperature bị đặt lại `0`.
- Mức độ: `high`, bắt buộc sửa.
- Người xử lý: `opencode-agent`.
- Hướng sửa gợi ý: sau khi PUT/reset thành công, đồng bộ trực tiếp trong handler
  (`const synced = valuesFromConfig(next)`; `setValues(synced)`; `setSavedSnapshot(synced)`;
  `previousServerRef.current = synced`) rồi mới cập nhật cache; bỏ `forceSyncRef`.
- Cách xác nhận: thêm test vào `ConfigView.cache.test.jsx` cho hai kịch bản trên (khôi phục khi dữ
  liệu không đổi; cập nhật từ ngoài sau đó vẫn giữ trường đang sửa); chạy lại `npm test`.
- Trạng thái: `resolved` (xác nhận ở vòng 3, `2026-10-27T07:45:42+07:00`).

### R-06 — Lưu riêng API key LLM không xoá bản nháp; form kẹt trạng thái "đã sửa"

- Vị trí: `frontend/src/ModelsView.jsx` — `LlmSection`, `initialKey` / `useMemo(..., [initialKey])`.
- Vấn đề: `initialKey` chỉ gồm provider, model, endpoint…, không gồm `*_has_key`. Khi người dùng chỉ
  nhập API key rồi lưu, `initial` không đổi nên effect `setDraft(initial)` không chạy; `apiKey` vẫn
  nằm trong bản nháp, `isLlmDirty` trả `true` (vì `apiKey.trim()` khác rỗng): nút Lưu vẫn sáng,
  cảnh báo `beforeunload` vẫn bật, bấm Lưu lần nữa gửi lại khoá. Bản trên `fbeca75` memo theo JSON
  toàn bộ `llm` nên lần lưu khoá đầu tiên (`has_key` từ `false` sang `true`) có reset bản nháp → đây
  là hồi quy.
- Mức độ: `medium`, bắt buộc sửa (hồi quy do thay đổi trong task).
- Người xử lý: `opencode-agent`.
- Hướng sửa gợi ý: sau khi `saveConfig` thành công, gọi `setDraft(llmDraftFromConfig(next.llm))`
  (tương tự cho `RerankerSection`) thay vì chỉ trông vào thay đổi `initialKey`; giữ `initialKey` để
  lưu ở tab Cấu hình RAG không xoá bản nháp.
- Cách xác nhận: test component — nhập API key, lưu, kiểm tra ô key rỗng và mục không còn dirty.
- Trạng thái: `resolved` (xác nhận ở vòng 3, `2026-10-27T07:45:42+07:00`).
- Ghi chú: xác định bằng đọc mã và đối chiếu `git show HEAD:frontend/src/ModelsView.jsx`; chưa có
  test tái lập.

### R-07 — `ChatView` mở hội thoại không truyền `signal`

- Vị trí: `frontend/src/ChatView.jsx`, nhánh mở hội thoại (`conversationsApi.get(id)`).
- Vấn đề: nhánh `if (isAbortError(error)) return;` không bao giờ xảy ra vì không truyền `signal`;
  `implementation.md` ghi `ChatView` dùng `signal` để huỷ khi unmount/đổi tài liệu, thực tế chỉ luồng
  stream có. Mở nhanh hai hội thoại vẫn có thể để response cũ ghi đè (hành vi có từ trước).
- Mức độ: `low`, không bắt buộc.
- Hướng theo dõi: truyền `AbortController` theo lượt mở và huỷ lượt trước, hoặc sửa lại mô tả.
- Trạng thái: `resolved` (xác nhận ở vòng 3, `2026-10-27T07:45:42+07:00`).

### R-08 — `describeError` bỏ `detail` của backend với mọi mã 5xx

- Vị trí: `frontend/src/api/errors.js`, nhánh `error.status >= 500`.
- Vấn đề: toast và màn lỗi luôn dùng `serverDetail` chung, kể cả khi 5xx có `detail` có ích (vd.
  proxy/LLM gateway hoặc HTTPException 5xx thêm sau này). Hiện `routes.py` chỉ chủ động trả 4xx
  (upload chuyển tiếp 400/413) nên ảnh hưởng nhỏ.
- Mức độ: `low`, không bắt buộc.
- Hướng theo dõi: ưu tiên `error.detail` khi `code === "http"` và detail không phải chuỗi mặc định
  theo mã trạng thái.
- Trạng thái: `resolved` (xác nhận ở vòng 3, `2026-10-27T07:45:42+07:00`).

### Đánh giá vòng 2

- Thiết kế lớp `api/` tốt: `request()` tách đúng timeout và huỷ bởi caller, chuẩn hoá lỗi FastAPI
  (kể cả `detail` dạng mảng 422), timeout dài cho upload/parse/chunk, NDJSON gói gọn trong
  `api/chat.js`. Query key và invalidate theo tiền tố `["documents"]` hợp lý.
- AC-02 chưa đạt đầy đủ do R-05; test component hiện có chỉ phủ trường hợp dữ liệu máy chủ thay đổi.
- Trạng thái `done` trong `task.md` dựa trên `self_review`; theo quy ước, coordinator cần đưa task về
  `in_progress` cho tới khi R-05, R-06 được xử lý, verifier chạy lại AC-02/AC-06 và reviewer xác nhận.

### Kết luận vòng 2

`changes_requested`. Bắt buộc: R-05 (`high`), R-06 (`medium`). Không bắt buộc: R-07, R-08.

---

## Vòng 1 — lịch sử

- Trạng thái lúc đó: `approved`
- Reviewer: `opencode-agent`
- Hình thức: `self_review` (chỉ có một agent trong phiên)
- Bản được review: working tree nhánh `feat/api-client-state` tại
  `2026-10-27T00:46:58+07:00`.
- Ghi chú: các mục R-05 … R-08 và câu cuối của "Đánh giá"/"Kết luận" bên dưới do `opencode-agent`
  thêm lúc `2026-10-27T07:41:08+07:00` như phản hồi sửa lỗi; xác nhận hiệu lực nằm ở vòng 3.
- Bằng chứng: `verification.md` mục AC-01 … AC-06.

## Phạm vi đã đọc

- `frontend/src/api/client.js`, `errors.js`, `chat.js`, `documents.js`, `conversations.js`, `config.js`,
  `queryClient.js`, `index.js`.
- `App.jsx`, `ChatView.jsx`, `ConfigView.jsx`, `ModelsView.jsx`, `DatasetView.jsx`, `DocumentView.jsx`,
  `main.jsx`, các component `ConversationList`, `MarkdownEditorView`, `ParserSelectionModal`,
  `OriginalDocumentViewer`, `lib/configDraft.js`, `lib/format.js`.
- Test `api/client.test.js`, `lib/configDraft.test.js`, `ConfigView.cache.test.jsx`, `package.json`.

## Nhận xét

### R-01 — Vòng effect do mảng rỗng fallback (đã xử lý)

- Vị trí: `DatasetView` (bản trong lúc triển khai).
- Vấn đề: `documents = data?.documents ?? []` tạo mảng mới mỗi render; effect khởi tạo `enabledDocs`
  chạy lại và set state mới, có thể lặp vô hạn khi chưa có dữ liệu.
- Mức độ: `high`, bắt buộc sửa.
- Xử lý: dùng hằng số `NO_DOCUMENTS` để giữ nguyên tham chiếu; đã kiểm tra bằng `npm test` và build.
- Trạng thái: `resolved`.

### R-02 — Query retry làm chậm thông báo timeout (đã xử lý)

- Vị trí: `api/queryClient.js`.
- Vấn đề: mặc định `retry: 1` khiến lỗi timeout 30 giây chỉ hiện sau lượt retry thứ hai.
- Mức độ: `medium`, bắt buộc sửa để khớp AC-03.
- Xử lý: đặt `retry: 0`; test timeout và toàn bộ test đều đạt.
- Trạng thái: `resolved`.

### R-03 — Stream chat không có timeout sau khi nhận header

- Vị trí: `api/chat.js`, `ChatView`.
- Vấn đề: nếu backend ngừng gửi dữ liệu giữa stream, request không tự hết giờ.
- Mức độ: `low`, không bắt buộc trong phạm vi phiếu (yêu cầu timeout cho API thường; chat đã có nút Dừng).
- Hướng theo dõi: thêm idle timeout cho từng lần `reader.read()` ở task streaming sau.
- Trạng thái: `deferred`.

### R-04 — Upload/parse rất lớn có thể vượt 5 phút

- Vị trí: `api/documents.js`.
- Vấn đề: timeout cố định 5 phút cho upload/parse/chunk; PDF cực lớn hoặc LlamaParse chậm có thể vượt.
- Mức độ: `low`, không bắt buộc; trước đây các request này không có timeout và có thể treo vô hạn.
- Hướng theo dõi: chuyển sang job nền có tiến độ nếu cần.
- Trạng thái: `deferred`.

### R-05 — Reset/save không cập nhật form khi response trùng cache (đã xử lý)

- Vị trí: `ConfigView.handleSaveAll`, `handleResetConfig`.
- Vấn đề: cờ `forceSyncRef` chỉ được xoá trong effect theo `serverValues`; nếu TanStack Query giữ nguyên
  object do dữ liệu trùng, effect không chạy, form giữ giá trị cũ và cờ bật sang lần cập nhật sau, xoá
  bản nháp đang sửa.
- Mức độ: `high`, bắt buộc sửa.
- Xử lý: bỏ cờ; thêm `applyServerConfig(response)` đặt thẳng `values`, `savedSnapshot` và
  `previousServerRef` sau save/reset. Test reset khi response trùng cache và test sửa tiếp sau reset đều
  đạt.
- Trạng thái: `resolved`.

### R-06 — Lưu chỉ API key vẫn hiện trạng thái chưa lưu (đã xử lý)

- Vị trí: `ModelsView.LlmSection.handleSave`.
- Vấn đề: `initialKey` chỉ theo dõi provider/model nên effect không reset draft khi chỉ đổi cờ `has_key`;
  khoá còn trong input, `dirty` vẫn true.
- Mức độ: `medium`, bắt buộc sửa.
- Xử lý: sau khi lưu, dựng lại draft từ `next.llm` và xoá trạng thái lỗi/test result. Test lưu chỉ API
  key xác nhận input rỗng và nút Lưu bị vô hiệu.
- Trạng thái: `resolved`.

### R-07 — Mở hội thoại không có tín hiệu huỷ (đã xử lý)

- Vị trí: `ChatView.loadConversation`.
- Vấn đề: request mở hội thoại không nhận `signal`, nên nhánh bỏ qua `AbortError` không bao giờ chạy.
- Mức độ: `low`, không bắt buộc.
- Xử lý: thêm `conversationAbortRef`; huỷ khi mở hội thoại khác, reset hoặc unmount, và truyền signal
  vào `conversationsApi.get`.
- Trạng thái: `resolved`.

### R-08 — Lỗi 5xx làm mất chi tiết backend (đã xử lý)

- Vị trí: `api/errors.js`.
- Vấn đề: mọi 5xx trả cùng một câu chung, bỏ `detail` backend.
- Mức độ: `low`, không bắt buộc.
- Xử lý: nối chi tiết backend vào mô tả 5xx khi thông điệp không phải câu mặc định do client tạo; thêm
  test `api/errors.test.js`.
- Trạng thái: `resolved`.

## Đánh giá

- Phạm vi đúng phiếu: toàn bộ `fetch` chuyển vào `api/`, không đổi backend.
- `request()` có timeout, chuẩn hoá `ApiError{status, detail}`, xử lý abort của caller riêng với timeout.
- Cache `/config` dùng chung và có test component chứng minh cập nhật giữa hai tab, kể cả giữ bản nháp.
- Phân loại lỗi tập trung; toast và màn lỗi dùng cùng một nguồn.
- Không còn `refreshDocCount`, `onChanged`, `reloadToken`, `conversationsToken`; danh sách tài liệu và
  hội thoại dùng query + invalidate.
- Test và build đều đạt; các rủi ro còn lại không chặn nghiệm thu.
- Vòng sửa R-05 … R-08 đã được kiểm lại: 58 test đạt, build thành công.

## Kết luận

`approved` trên bản working tree nêu trên. Không còn nhận xét bắt buộc chưa xử lý.

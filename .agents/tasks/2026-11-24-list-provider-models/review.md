# Review: 2026-11-24-list-provider-models

- Reviewer: `claude-agent`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: nhánh `feat/list-provider-models` (S-01, S-02, sửa R-03 và S-03), toàn bộ diff so với `25d8a32`.
- Cập nhật lúc: `2026-11-24T22:33:18+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-04; S-01, S-02.
- File/thay đổi cần đọc: các file trong phạm vi `plan.md`.
- Bằng chứng kiểm chứng: V-01..V-04.
- Điểm cần đánh giá: rò khoá (host lạ, nhà cung cấp khác, response/log), SSRF qua Base URL, race giữa các request,
  trải nghiệm khi nhà cung cấp không liệt kê được.

## Nhận xét

### R-01 — Lọc mô hình LLM theo tên có thể ẩn mô hình hợp lệ

- Vị trí: `backend/app/core/provider_models.py` `_NON_CHAT_MARKERS`, `_filter_openai`.
- Liên quan: AC-01.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: `/models` chuẩn OpenAI không ghi loại mô hình nên lọc theo tên; qua proxy (OpenRouter, LiteLLM)
  một mô hình chat có tên chứa `image`/`audio` sẽ không có trong danh sách.
- Đề nghị xử lý: giữ; admin bấm "Nhập tên khác". Nếu gặp thực tế thì thu hẹp danh sách từ khoá.
- Người xử lý: `claude-agent`.
- Nếu deferred: không ảnh hưởng lưu/dùng mô hình; theo dõi khi có phản hồi.

### R-02 — Tự tải khi rời ô Base URL có thể báo 401 trước khi admin nhập khoá

- Vị trí: `frontend/src/models/ModelKindPanel.jsx` `autoLoadModels`.
- Liên quan: AC-03.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: với nhà cung cấp khoá tuỳ chọn (tương thích OpenAI), rời ô Base URL tự tải khi chưa có khoá; máy
  chủ cần khoá sẽ trả 401 và hiện "Kiểm tra API key." cho tới khi admin nhập khoá (rời ô khoá thì tự tải lại).
- Đề nghị xử lý: giữ — Ollama/vLLM nội bộ (trường hợp chính) không cần khoá; thông báo chỉ dẫn đúng bước tiếp theo.
- Người xử lý: `claude-agent`.
- Nếu deferred: theo dõi phản hồi người dùng.

### R-03 — Kết quả về muộn có thể tự điền mô hình vào cấu hình đã đổi

- Vị trí: `frontend/src/models/ModelKindPanel.jsx` `loadModels`.
- Liên quan: AC-03.
- Mức độ: `medium`.
- Bắt buộc sửa: có.
- Trạng thái: `resolved`.
- Vấn đề và tác động: request đang chờ (ví dụ TEI một mô hình), admin đổi sang nhà cung cấp khác; khi kết quả về, bước
  "một mô hình thì tự điền" ghi tên mô hình TEI vào ô của nhà cung cấp mới.
- Đề nghị xử lý: chỉ tự điền khi chữ ký cấu hình hiện tại vẫn khớp chữ ký lúc gửi.
- Người xử lý: `claude-agent`.
- Phản hồi/cách sửa: `setDraft` kiểm `modelListSignature(kind, current) !== signature` trước khi điền.
- Bằng chứng sau sửa: `npx vitest run src/models` → `26 passed`.
- Xác nhận của reviewer: đã đọc lại; danh sách hiển thị vốn đã lọc theo chữ ký, giờ tự điền cũng vậy.

Các điểm đã kiểm không có vấn đề: Base URL kiểm allowlist trước khi lấy khoá (route) và kiểm lại trong module; hãng URL
cố định bỏ Base URL client; khoá Gemini trong header, không trong URL; `httpx.get` không theo redirect; thông báo lỗi
không chứa body/khoá; khoá profile chỉ dùng khi cùng loại và cùng nhà cung cấp; khoá `.env` không gửi tới máy chủ tương
thích; endpoint chỉ cho admin.

## Lịch sử các vòng review

- `2026-11-24T22:33:18+07:00` — claude-agent — working tree S-01 + S-02 — `changes_requested` (R-03); R-01, R-02 deferred.
- `2026-11-24T22:33:18+07:00` — claude-agent — working tree sau sửa R-03 — `approved`.
- `2026-11-24T22:44:10+07:00` — claude-agent — S-03 (diff so với `9e65a5a`) — `approved`, không có nhận xét mới. Đã đọc:
  mọi chỗ còn dùng `description`/`hint`/`hintId` (không còn `aria-describedby` trỏ tới id đã bỏ), không còn import
  thừa (`sendsDocumentsToService`), cảnh báo `VECTOR_DIM` và lỗi tải danh sách vẫn hiện.
- `2026-11-24T22:47:51+07:00` — claude-agent — bỏ placeholder Endpoint/Mô hình/API key — `approved`, không có nhận xét mới; nhãn
  "Đã lưu khoá"/"Dùng … nếu để trống" vẫn thay cho thông tin placeholder cũ của ô khoá.
- `2026-11-24T22:49:13+07:00` — claude-agent — bỏ nhãn "Dùng … .env nếu để trống" — `approved`, không có nhận xét mới. Ghi nhận: admin không
  còn thấy trong hộp thoại rằng để trống khoá OpenAI/Gemini/Azure sẽ dùng khoá `.env` (theo yêu cầu người dùng).

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01, R-02 (theo dõi phản hồi thực tế).
- Phần chưa review / giới hạn: self_review, không phải review độc lập; chưa gọi API thật của từng hãng.
- Bước tiếp theo: commit, mở PR vào `dev`.

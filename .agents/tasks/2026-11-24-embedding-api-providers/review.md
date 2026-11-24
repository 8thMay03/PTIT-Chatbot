# Review: 2026-11-24-embedding-api-providers

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (cùng agent triển khai, không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `feat/embedding-api-providers` (tách từ `dev` tại `49c1090`), toàn bộ `git diff` và
  4 file mới (`app/embeddings/api_clients.py`, `app/embeddings/errors.py`, `tests/test_embedding_api_clients.py`,
  `tests/test_embedding_api_profiles.py`).
- Cập nhật lúc: `2026-11-24T17:50:32+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 … AC-09, S-01 … S-05, quyết định D-01 … D-05.
- File/thay đổi cần đọc: 22 file sửa (740 dòng thêm, 102 dòng xoá) và 4 file mới.
- Bằng chứng kiểm chứng: V-01 … V-09 trong `verification.md`. Chưa kiểm chứng gọi dịch vụ thật.
- Điểm cần đánh giá:
  - Bảo mật: khoá trong response/log/DOM; gửi khoá sang host lạ hoặc hãng khác; SSRF qua Base URL hoặc tên mô hình
    Gemini.
  - Đúng đắn: thứ tự vector khi chia lô; đệm 0; tương thích ngược vector OpenAI 1536 và cache eval; dấu vân tay.

## Đã kiểm tra, không có vấn đề

- Khoá:
  - Chỉ đi trong header và không có trong `reason`/log.
  - `test-embedding` kiểm URL trước khi lấy khoá. Chỉ lấy khoá profile embedding cùng provider, nên khoá Voyage không
    được gửi sang Jina.
  - Đổi hãng thì khoá cũ bị xoá như trước; với hãng bắt buộc khoá thì phải nhập khoá mới.
- SSRF:
  - Adapter riêng dùng URL cố định. `openai_compatible` qua allowlist lúc lưu, lúc áp profile và mỗi lần gọi.
  - Không theo redirect (mặc định của `httpx.post`).
  - Tên mô hình Gemini được `quote(safe="")` nên không đổi được path.
- Tương thích ngược:
  - `text-embedding-3-small` với `EMBEDDING_DIMENSION` trống: không gửi `dimensions`, không bọc đệm 0. Request và vector
    như cũ.
  - Cache eval giữ khoá cũ với mô hình không phân biệt câu hỏi.
  - `embed(texts)` giữ chữ ký nên các fake/wrapper hiện có vẫn chạy.
- `EmbeddingAPIError` kế thừa `EmbeddingUnavailableError`: các route nạp tài liệu/kiểm tra tìm kiếm trả 503 với lý do an
  toàn. Lỗi tạm thời không ghim embedder ở `error`.

## Nhận xét

### R-01 — Danh sách mô hình có số chiều cố định viết cứng

- Vị trí: `backend/app/embeddings/api_clients.py` `_FIXED_DIMENSION_MODELS`, `_JINA_TASK_PREFIXES`.
- Liên quan: AC-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: mô hình không có trong danh sách được coi là đổi được số chiều và nhận tham số số chiều. Nếu hãng
  ra mô hình mới có số chiều cố định, dịch vụ trả 400. "Kiểm tra kết nối" sẽ báo lỗi này trước khi admin chọn dùng.
- Đề nghị xử lý: cập nhật danh sách khi hãng đổi mô hình.
- Người xử lý: `claude-agent`.
- Nếu deferred: đổi được bằng một dòng; lỗi hiện rõ ở bước kiểm tra kết nối. Theo dõi khi có báo lỗi thực tế.

### R-02 — Mỗi câu hỏi gọi API embedding, không cache

- Vị trí: `ApiEmbeddingModel.embed_query`.
- Liên quan: AC-05.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: mỗi câu hỏi tốn một request (tối đa 15 s), giống OpenAI hiện tại. Khi dịch vụ lỗi, câu hỏi lỗi
  theo D-05, không quay về chỉ dùng BM25.
- Đề nghị xử lý: nếu cần, làm task riêng cho cache embedding câu hỏi hoặc quay về BM25 khi API lỗi.
- Người xử lý: `claude-agent`.
- Nếu deferred: đúng quyết định D-05 người dùng đã chọn.

## Lịch sử các vòng review

- 2026-11-24T17:42:32+07:00 — claude-agent — working tree trên `49c1090` — `approved`. R-01, R-02 `deferred` (không bắt
  buộc). Trong lúc review đã sửa: chuẩn hoá tiền tố `models/` khi xét mô hình Gemini có số chiều cố định; lỗi ruff ở file
  mới. Chạy lại test liên quan: đạt.
- 2026-11-24T17:50:32+07:00 — claude-agent — working tree, phần S-06 (`frontend/src/models/fields.jsx`) — `approved`.
  - Đã đọc diff logo: SVG nội tuyến, không thêm dependency, ghi nguồn và giấy phép.
  - `useId` đã bỏ ký tự đặc biệt trước khi dùng trong `url(#…)`; không đổi API của `ProviderIcon`.
  - Đối chiếu V-10. Không có nhận xét mới.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01, R-02 (lý do ở trên).
- Phần chưa review / giới hạn: không gọi được dịch vụ thật để đối chiếu định dạng response.
- Bước tiếp theo: coordinator đóng task; người dùng thử "Kiểm tra kết nối" với khoá thật rồi commit/PR khi muốn.

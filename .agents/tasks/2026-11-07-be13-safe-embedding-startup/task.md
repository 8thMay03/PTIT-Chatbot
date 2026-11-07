# Task: BE-13 · Khởi động an toàn: app không sập khi thiếu key embedding; bỏ fallback hash âm thầm

- ID: `2026-11-07-be13-safe-embedding-startup`
- Trạng thái: `in_review`
- Coordinator: `claude-be13`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-07T17:17:49+07:00`
- Cập nhật lúc: `2026-11-07T17:33:32+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: Notion "PTIT Chatbot" › BE-13 (P0, rà soát toàn hệ thống ngày 2026-11-05) — https://app.notion.com/p/40f334d296eb81a7a9effc2cdc695d95

Hành vi hiện tại (đối chiếu trên `origin/dev` @ `6257004`, đã gồm BE-11 / PR #50 và BE-10 / PR #51):

- Embedder được tạo **lúc import module**: `retriever = Retriever()` (`backend/app/retrieval/retriever.py:35`) và `ingestion_pipeline = IngestionPipeline()` (`backend/app/ingestion/pipeline.py:942`) đều gọi `create_embedding_model()` trong `__init__`.
- Thiếu `OPENAI_API_KEY`/`EMBEDDING_API_KEY` thì `OpenAIEmbeddingModel.__init__` ném `ValueError` (`backend/app/embeddings/models.py:32-34`) → `import app.main` thất bại → toàn bộ API (kể cả trang admin để nhập key) không khởi động. Xảy ra cả khi key đã lưu trong DB qua `/config` (trường `openai_api_key` thuộc `PERSISTED_FIELDS`), vì `load_persisted_config()` chỉ chạy trong `lifespan` (`backend/app/main.py:15-21`), sau bước import.
- `create_embedding_model()` (`backend/app/embeddings/embedder.py:10-27`): provider `sentence-transformers` lỗi tải model, hoặc provider không có trong danh sách (`cohere`, `gemini` vẫn được liệt kê ở `get_runtime_config_dict`), đều **âm thầm** trả `HashEmbeddingModel()` 384 chiều, trong khi cột là `Vector(1536)` (`backend/app/db/models.py:165`) và `VECTOR_DIM=1536`. Kết quả: chia đoạn ghi vector rác hoặc lỗi DB khó hiểu, truy hồi vector vô nghĩa.
- `model_profiles.load_selected_embedding` phải tự dò `isinstance(model, HashEmbeddingModel)` để đoán fallback (`backend/app/core/model_profiles.py:485-488`).
- `/api/health` (`backend/app/api/routes.py:165`) chỉ báo DB; không cho biết embedding có dùng được không. Docker healthcheck gọi route này (`docker-compose.yml:61`).

Kết quả cần có:

- `import app.main` và khởi động app **không** cần key embedding. Embedder được tạo lười (lần dùng đầu hoặc lúc `lifespan` sau `load_persisted_config` + profile embedding).
- Khi embedding chưa cấu hình/không dùng được: `/api/health` vẫn HTTP 200 và có trường `embedding` (`ready` | `not_configured` | `error`); `/api/chat` và `/api/chat/stream` trả **503** với thông điệp tiếng Việt rõ ràng, không ghi DB, không gọi LLM; các route chia đoạn của admin trả 503 thay vì 500; trang admin vẫn vào được và hiện lý do.
- Admin lưu key (qua `/config` hoặc chọn profile embedding) khi embedder **chưa chạy được** thì chat hoạt động ngay, không cần restart.
- Chỉ dùng `HashEmbeddingModel` khi `EMBEDDING_PROVIDER=hash` khai báo rõ; không còn fallback âm thầm. Số chiều vector được kiểm tra; sai số chiều → lỗi rõ, không ghi vector sai chiều.

## Phạm vi

- Bao gồm: `backend/app/embeddings/` (runtime lười, lỗi có kiểu, bỏ fallback, kiểm số chiều); `Retriever`/`IngestionPipeline` dùng runtime chung; `backend/app/main.py` (lifespan); `backend/app/core/model_profiles.py` (áp profile qua runtime, áp ngay khi embedder chưa chạy được, trạng thái runtime cho admin); `/api/health`; kiểm tra 503 trong `chat`/`chat_stream` và các route chia đoạn; `.env.example` (chú thích); test.
- Ngoài phạm vi:
  - Đổi embedder **đang chạy tốt** lúc runtime (đổi provider/model/key của embedder đã `ready` vẫn cần restart như hiện tại — tránh trộn hai không gian vector).
  - Nạp lại/embed lại dữ liệu khi đổi model (BE-15).
  - Giao diện admin mới: dùng `embedding_runtime.load_error` đã có trong `ModelKindPanel.jsx`; không sửa frontend, trừ khi kiểm tra thủ công thấy 503 hiện sai (khi đó ghi nhận cho FE-15).
  - Đổi cột `Vector(1536)` hay hỗ trợ `VECTOR_DIM` khác 1536 (chỉ phát hiện và báo lỗi).
  - Lớp LLM (BE-12).
- Ràng buộc:
  - `/api/health` luôn HTTP 200 khi DB ổn (docker healthcheck của frontend phụ thuộc); không lộ chi tiết lỗi/khóa ra route công khai.
  - Không đổi hợp đồng NDJSON, cookie, 404, 422/429 của BE-10/BE-11. Thứ tự: 422 → 400 câu rỗng → **503 embedding** → 429 IP → pha (a). Request 503 không trừ hạn mức.
  - Runtime an toàn khi nhiều thread (route sync, threadpool stream, job nền).
  - Test hiện có không phụ thuộc key thật vẫn pass; test mới không gọi mạng.
  - Không ghi key/secret vào log hay `load_error`.

## Tiêu chí nghiệm thu

- [x] AC-01: `OPENAI_API_KEY= EMBEDDING_API_KEY= python -c "import app.main"` thành công; `TestClient(app)` (có lifespan) khởi động được không có key; `/api/health` trả 200 với `embedding: "not_configured"`.
- [x] AC-02: Khi embedding không dùng được, `/api/chat` và `/api/chat/stream` trả **503** với thông điệp tiếng Việt; không tạo hội thoại/tin nhắn, không gọi retrieval/LLM, không trừ hạn mức BE-10. Các route admin đăng nhập/cấu hình/model-profiles vẫn dùng được; route chia đoạn trả 503 và không đổi trạng thái tài liệu.
- [x] AC-03: Từ trạng thái `not_configured`, lưu `openai_api_key` qua `PUT /api/config` **hoặc** chọn profile embedding hợp lệ → request chat kế tiếp dùng được embedding (test với embedder giả, không restart); `/api/health` chuyển `ready`.
- [x] AC-04: `sentence-transformers` tải lỗi hoặc provider không hỗ trợ → `embedding: "error"` kèm lý do (cho admin), không tạo `HashEmbeddingModel`, không vector 384 chiều nào được ghi. `EMBEDDING_PROVIDER=hash` vẫn hoạt động và dùng `VECTOR_DIM` chiều.
- [x] AC-05: Vector có số chiều khác `VECTOR_DIM` (model trả sai chiều, hoặc `VECTOR_DIM` khác cột `Vector(1536)`) → lỗi rõ, chuyển `error`, không ghi chunk/vector nào.
- [x] AC-06: Embedder đã `ready` không bị thay ngầm khi cấu hình đổi lúc chạy; `restart_required`/`load_error` của `/api/model-profiles` vẫn đúng. Toàn bộ test backend pass.

## Tài liệu và phụ thuộc

- Notion BE-13: https://app.notion.com/p/40f334d296eb81a7a9effc2cdc695d95
- Nền: `origin/dev` @ `6257004` (BE-10, BE-11 đã merge). Task registry mô hình: `.agents/tasks/2026-10-30-model-registry/`; lưu cấu hình: `.agents/tasks/2026-10-28-persist-runtime-config/`.
- Liên quan: BE-12 (lớp LLM — cùng chạm `routes.py`, không làm song song khối chat), BE-15 (embed lại), FE-15 (hiển thị lỗi chat, 503), BE-10 (thứ tự kiểm tra chat).
- Code: `backend/app/embeddings/{embedder,models,__init__}.py`, `backend/app/retrieval/retriever.py`, `backend/app/ingestion/pipeline.py`, `backend/app/core/model_profiles.py`, `backend/app/main.py`, `backend/app/api/routes.py` (`health`, `chat`, `chat_stream`, route ingest/chunk), `backend/app/api/schemas.py` (`EmbeddingRuntime` nếu thêm trường), `backend/tests/conftest.py`, `backend/tests/test_model_profiles.py`, `.env.example`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Câu hỏi mở cho người yêu cầu

- Q-01: Embedder đã `ready` có cho thay nóng khi admin đổi key không? Đề xuất **không** — chỉ áp nóng khi embedder đang `not_configured`/`error`; đã `ready` thì giữ hành vi "cần restart" hiện tại (đổi model lúc chạy dễ trộn không gian vector; xoay key là việc hiếm).
- Q-02: Chọn profile embedding khi embedder chưa chạy được thì áp ngay (thay vì chờ restart)? Đề xuất **có** — đây là đường chính để admin "nhập key qua trang admin" theo Notion.
- Q-03: Khi embedding không `ready`, `status` tổng của `/api/health` là gì? Đề xuất **`degraded`** (HTTP vẫn 200, docker healthcheck không đổi); thêm `embedding: ready|not_configured|error`, không kèm chi tiết lỗi ở route công khai.
- Q-04: `cohere`, `gemini` đang được liệt kê là provider embedding nhưng chưa có cài đặt. Đề xuất **giữ danh sách, chỉ báo lỗi "chưa hỗ trợ"** trong task này (bỏ khỏi danh sách đụng tới frontend — để task sau).

## Quyết định cho câu hỏi mở

Người yêu cầu giao "triển khai task be13" (2026-11-07) mà không đổi đề xuất → áp dụng đề xuất của Q-01..Q-04 như ghi ở trên: không thay nóng embedder đã `ready`; chọn profile embedding khi embedder chưa chạy được thì áp ngay; health `degraded` + trường `embedding`; giữ `cohere`/`gemini` trong danh sách, báo "chưa được hỗ trợ".

## Trạng thái hiện tại

- Tóm tắt: S-01..S-05 xong trên nhánh `feat/safe-embedding-startup` (tách từ `dev` @ `6257004`), chưa commit. AC-01..AC-06 có bằng chứng tự động `passed` (V-01..V-06); V-07 (UI) mới chạy phần API trên uvicorn thật, phần giao diện `not_run`. Self-review `approved`.
- Blocker: không.
- Bước tiếp theo: người yêu cầu xem diff, quyết định commit/PR; đề nghị một vòng review `independent` (như BE-10) và kiểm tra UI V-07 trước khi đóng `done`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-07T17:17:49+07:00 — claude-be13: tạo task `draft` từ Notion BE-13, dựa trên `origin/dev` @ `6257004`. Giới hạn thay nóng embedder ở trạng thái chưa chạy được (Q-01); để embed lại cho BE-15 và UX lỗi chat cho FE-15.
- 2026-11-07T17:33:32+07:00 — claude-be13: được giao triển khai → `in_progress`; chấp nhận đề xuất Q-01..Q-04. Mở rộng nhỏ có ghi trong `implementation.md` (D-02: sửa profile embedding đang chọn khi embedder chưa chạy được cũng áp ngay; D-01: `load()` thay `reload()`). Xong S-01..S-05 → `in_review`.

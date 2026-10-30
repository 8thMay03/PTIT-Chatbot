# Implementation: 2026-10-30-model-registry

## Tổng quan triển khai

Đã triển khai S-01 và S-02 trên nhánh `feat/model-registry` (tách từ `dev` tại `cc33fdd`).
Commit backend `0463d9b`; commit frontend + sửa sau self-review ở commit kế tiếp trên cùng nhánh.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-10-30T22:25:00+07:00`.
- Đã làm:
  - Bảng `model_profiles` (id, kind, name, provider, model, params JSON, encrypted_api_key; unique
    `(kind, name)`) + migration `0007` (guard `has_table` như 0005/0006).
  - `app/core/model_profiles.py`: kiểm tra theo `(loại, nhà cung cấp)` (trường thừa bị bỏ, URL qua
    allowlist, số chiều nguyên dương), CRUD, `activate_profile`, `resolve_llm_test_key`,
    `registry_state`, `load_selected_embedding(_at_startup)`.
  - Chọn LLM: về `.env` trước rồi chép trường của profile → override không giữ trường nhà cung cấp cũ.
    Profile không có khoá dùng khoá `.env` (trừ tương thích OpenAI). Chọn reranker: `cross-encoder` +
    model; `null` = heuristic. Chọn embedding: chỉ lưu `embedding_profile_id`, từ chối nếu số chiều ≠
    `VECTOR_DIM`.
  - `config_store`: thêm 3 trường `*_profile_id` vào `PERSISTED_FIELDS`; tách `settings_transaction`
    (rollback DB + phục hồi settings) dùng chung cho PUT /config và kho mô hình; PUT /config đổi trực
    tiếp trường nhà cung cấp LLM/reranker thì bỏ chọn profile.
  - `config.py`: trường `embedding_api_key`, `llm_profile_id`, `reranker_profile_id`,
    `embedding_profile_id`; reset không đụng `embedding_provider/model/api_key` (embedder đang chạy).
  - `embedder.py`: OpenAI embedding dùng `embedding_api_key` trước `openai_api_key`.
  - `main.py` lifespan: sau `load_persisted_config()` gọi `load_selected_embedding_at_startup()` — tạo
    lại embedder cho `retriever` và `ingestion_pipeline`; lỗi (thiếu profile, sai số chiều, khoá hỏng,
    sentence-transformers rơi về Hash) giữ embedder `.env`, ghi `load_error`.
  - Route `/api/model-profiles` (GET, POST, PUT/DELETE `{id}`, POST `activate`, POST `test-llm`), đều
    `require_admin`; tách `_run_llm_test` dùng chung với `/config/test-llm`.
  - Sau self-review (R-01): đổi nhà cung cấp mà không nhập khoá mới thì bỏ khoá cũ.
- Kiểm tra đã chạy: V-01..V-03.
- Còn lại/blocker: không có.

### S-02 — claude-agent

- Cập nhật lúc: `2026-10-30T22:25:00+07:00`.
- Đã làm:
  - `ModelsView.jsx` viết lại: ba tab con (`role="tablist"`, phím mũi tên, nhớ tab trong
    `localStorage`), panel giữ mounted; chuẩn hoá response kho để response lệch không vỡ màn.
  - `models/catalog.js`: nhà cung cấp/trường/kiểm tra/payload cho từng loại; tên mặc định = tên mô hình;
    tự điền số chiều cho mô hình nhúng quen thuộc.
  - `models/fields.jsx`: thành phần dùng chung tách từ ModelsView cũ (logo, pill, choice, text, API key
    có nút "Xoá khoá đã lưu").
  - `models/ModelKindPanel.jsx`: thẻ "Mô hình đang dùng" (select gồm lựa chọn `.env`/Heuristic + profile;
    profile embedding sai số chiều bị khoá; cảnh báo reranker tắt, chờ khởi động lại, `load_error`),
    form thêm/sửa (kiểm tra kết nối LLM dùng khoá đã lưu), danh sách với nhãn Đang dùng/Đang chạy/Đã lưu
    khoá/Khác VECTOR_DIM, xoá qua Modal (khoá nút với profile đang dùng).
  - `api/modelProfiles.js`, `queryKeys.modelProfiles`; mọi thao tác ghi đặt cache kho + invalidate config.
  - `styles/models.css`: tab con, danh sách; bỏ CSS hướng dẫn đổi embedding cũ.
  - Test: `models/catalog.test.js`, `models/ModelsView.test.jsx`; sửa mock trong
    `ConfigView.cache.test.jsx`, `admin/AdminApp.test.jsx`; bỏ test "lưu chỉ API key" của form LLM cũ
    (form đã thay bằng kho mô hình).
- Kiểm tra đã chạy: V-04, V-05.
- Còn lại/blocker: chưa kiểm tra giao diện bằng trình duyệt (V-06 `not_run`).

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

### HANDOFF-claude-agent-001 — S-01, S-02

- Từ / đến: `claude-agent` / `8thMay03`.
- Đã hoàn tất: kho mô hình ba loại + chọn mô hình đang dùng.
- File/branch/commit/patch: nhánh `feat/model-registry`.
- Kiểm chứng: `verification.md` (V-06 giao diện trình duyệt chưa chạy).
- Review: `review.md` — `approved` (self_review); R-01 resolved, R-02/R-03 deferred.
- Bước tiếp theo: người yêu cầu xem giao diện tại Settings → Mô hình, rồi merge vào `dev`.
- Phản hồi nhận bàn giao: <chờ người yêu cầu>.

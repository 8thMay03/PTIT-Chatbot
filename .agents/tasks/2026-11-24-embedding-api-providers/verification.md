# Verification: 2026-11-24-embedding-api-providers

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed` (trừ gọi dịch vụ thật, `not_run` — xem cuối file).
- Bản được kiểm tra: working tree nhánh `feat/embedding-api-providers` (tách từ `dev` tại `49c1090`), chưa commit.
- Môi trường: Windows 11, Python 3.11.5 (`backend/.venv`), Node v24.14.0, Postgres `ptit_chatbot_postgres` (Docker) đang
  chạy, vitest 3.2.7.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-agent / `2026-11-24T17:42:32+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q tests/test_embedding_api_profiles.py`.
- Kỳ vọng:
  - Voyage/Cohere/Gemini/Jina thiếu khoá thì 422; có khoá thì 201, `has_api_key`, response và DB không chứa khoá.
  - `openai_compatible` thiếu Base URL hoặc URL ngoài allowlist thì 422.
  - Đổi hãng không nhập khoá thì 422; đổi sang `sentence-transformers` thì xoá khoá.
- Kết quả thực tế: 18 passed. Các test liên quan: `test_vendor_profile_requires_key_and_hides_it[voyage|cohere|gemini|jina]`,
  `test_openai_compatible_profile`, `test_update_keeps_key_and_provider_change_clears_it`.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra pytest.

### V-02 — AC-02

- Người thực hiện / thời gian: claude-agent / `2026-11-24T17:42:32+07:00`.
- Loại: test tự động (`httpx.post` giả, không gọi mạng; conftest chặn mọi request thật).
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q tests/test_embedding_api_clients.py`.
- Kỳ vọng:
  - URL, header xác thực, body từng dịch vụ đúng; `input_type`/`task` đúng theo câu hỏi hay tài liệu.
  - Chỉ gửi tham số số chiều với mô hình hỗ trợ.
  - Vector đúng thứ tự, chia lô đúng; response sai định dạng thì lỗi.
- Kết quả thực tế: 38 passed.
  - Request: `test_voyage_request`, `test_cohere_request`, `test_gemini_request_uses_header_key_and_task_type`,
    `test_gemini_model_name_cannot_change_path`, `test_jina_v3_sends_task_and_dimensions_v2_does_not`,
    `test_openai_compatible_request_without_key`.
  - Response và chia lô: `test_openai_like_response_is_reordered_by_index`, `test_cohere_batches_keep_order`
    (200 đoạn → lô 96/96/8), `test_invalid_response_raises` (6 trường hợp).
- Trạng thái: `passed`.
- Bằng chứng: đầu ra pytest.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-agent / `2026-11-24T17:42:32+07:00`.
- Loại: test tự động.
- Lệnh / thao tác: như V-02, và pytest đầy đủ (V-09).
- Kỳ vọng: retriever gọi `embed_query`; nạp tài liệu gọi `embed`; OpenAI/Sentence-Transformers/Hash như cũ.
- Kết quả thực tế:
  - `test_retriever_embeds_question_as_query` passed.
  - `test_smaller_model_is_padded_to_vector_dim`: request lần lượt có `input_type` `document` rồi `query`.
  - Test cũ của runtime, pipeline, retrieval và eval (`test_eval_retrieval.py` với cache) đều passed trong lần chạy đầy
    đủ.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra pytest.

### V-04 — AC-04

- Người thực hiện / thời gian: claude-agent / `2026-11-24T17:42:32+07:00`.
- Loại: test tự động.
- Lệnh / thao tác: như V-01, V-02.
- Kỳ vọng:
  - Vector 1024 chiều được đệm 0 tới 1536 và cosine không đổi.
  - Trả sai số chiều thì runtime chuyển `error`.
  - `EMBEDDING_DIMENSION > VECTOR_DIM` thì lỗi; profile 2048 chiều không chọn dùng được, profile 1024 thì được.
- Kết quả thực tế: `test_smaller_model_is_padded_to_vector_dim`, `test_padding_keeps_cosine_similarity`,
  `test_wrong_dimension_from_api_marks_runtime_error`, `test_dimension_above_vector_dim_is_rejected`,
  `test_smaller_dimension_can_be_selected_larger_cannot` đều passed.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra pytest.

### V-05 — AC-05

- Người thực hiện / thời gian: claude-agent / `2026-11-24T17:42:32+07:00`.
- Loại: test tự động (`_sleep` giả).
- Lệnh / thao tác: như V-02.
- Kỳ vọng:
  - Nạp tài liệu: thử lại 429 theo `Retry-After`, thử lại 503 tối đa 4 lần (chờ 2/4/8 s), thử lại timeout; 401 không
    thử lại.
  - Câu hỏi: không thử lại, timeout 15 s.
  - Log và `reason` không chứa khoá hay nội dung đoạn.
  - Lỗi API không làm embedder chuyển `error` và là `EmbeddingUnavailableError` (để route trả 503).
- Kết quả thực tế: `test_document_retries_429_with_retry_after`, `test_document_gives_up_after_max_attempts`,
  `test_timeout_is_retried`, `test_client_error_is_not_retried`, `test_query_is_not_retried_and_uses_short_timeout`,
  `test_api_error_does_not_mark_runtime_error`, `test_api_error_is_embedding_unavailable_for_existing_503_handlers`
  đều passed.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra pytest.

### V-06 — AC-06

- Người thực hiện / thời gian: claude-agent / `2026-11-24T17:42:32+07:00`.
- Loại: test tự động.
- Lệnh / thao tác: như V-01, kèm `tests/test_model_profiles.py` và `tests/test_safe_embedding_startup.py`.
- Kỳ vọng:
  - Áp profile đặt đúng provider/model/khoá/Base URL/số chiều; lỗi tạo embedder thì khôi phục settings cũ.
  - Sửa số chiều của profile đang chạy thì `restart_required`.
  - Dấu vân tay runtime đổi theo khoá, Base URL, số chiều.
- Kết quả thực tế: `test_load_selected_embedding_applies_all_fields`, `test_load_failure_restores_previous_settings`,
  `test_fingerprint_tracks_key_base_url_and_dimension` passed. Test áp embedding cũ (`test_embedding_selection_applies_at_startup`,
  `test_selecting_embedding_profile_applies_now_when_not_running`…) passed.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra pytest (104 passed cho ba file profile/API).

### V-07 — AC-07

- Người thực hiện / thời gian: claude-agent / `2026-11-24T17:42:32+07:00`.
- Loại: test tự động.
- Lệnh / thao tác: như V-01.
- Kỳ vọng:
  - Endpoint cần admin, dùng khoá đã lưu hoặc khoá nhập tay, không lưu gì.
  - Không gửi khoá profile của hãng khác.
  - Báo lệch số chiều; lỗi 401 kèm gợi ý; 422 khi provider cục bộ/thiếu mô hình/thiếu hoặc sai Base URL (không gọi
    dịch vụ).
  - `openai_compatible` không khoá thì không có header `Authorization`.
- Kết quả thực tế: `test_test_embedding_requires_admin`, `test_test_embedding_uses_stored_key_and_saves_nothing`,
  `test_test_embedding_does_not_send_key_of_other_provider`, `test_test_embedding_reports_dimension_mismatch_and_http_errors`,
  `test_test_embedding_rejects_invalid_request` (4 trường hợp), `test_test_embedding_openai_compatible_without_key`
  đều passed.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra pytest.

### V-08 — AC-08

- Người thực hiện / thời gian: claude-agent / `2026-11-24T17:42:32+07:00`.
- Loại: test tự động + kiểm tra thủ công qua ảnh chụp.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác:
  - `npx vitest run src/models`: 20 passed.
    - Test mới "embedding: thêm Voyage AI với khoá bắt buộc, số chiều tự điền, ghi chú đệm 0 và kiểm tra kết nối".
    - Test catalog mới "embedding qua API…".
  - Ảnh chụp: Playwright (`playwright-core` trong scratchpad, Chromium cài sẵn), Vite cổng 5391, `/api/**` giả lập.
    Thao tác: `/admin#settings/models-embedding` → Thêm mô hình → Voyage AI → `voyage-3.5` → khoá → Kiểm tra kết nối.
- Kỳ vọng:
  - Hộp thoại có 7 nhà cung cấp và ô khoá "Bắt buộc"; số chiều tự điền 1024; có ghi chú đệm 0 và ghi chú gửi dữ liệu.
  - Thiếu khoá thì báo lỗi, không gửi request; payload kiểm tra/tạo đúng; khoá không xuất hiện trong DOM.
  - Danh sách hiện "Voyage AI · voyage-3.5 · 1024 chiều", nút "Dùng" bật; mô hình 3072 chiều có nhãn "Vượt VECTOR_DIM"
    và nút "Dùng" bị khoá.
- Kết quả thực tế: đạt cả test và ảnh.
  - Ảnh (scratchpad phiên, `shots/out/`): `embedding-voyage-light.png`, `embedding-voyage-dark.png`,
    `embedding-list-light.png`, `embedding-list-dark.png`.
  - Đã xem ảnh: chữ và ghi chú đọc rõ ở cả hai theme. Danh sách hiện Cohere v4 1536 chiều có nút Dùng, OpenAI large
    3072 chiều có nhãn "Vượt VECTOR_DIM".
- Trạng thái: `passed`.
- Bằng chứng: đầu ra vitest, ảnh chụp.

### V-09 — AC-09

- Người thực hiện / thời gian: claude-agent / `2026-11-24T17:42:32+07:00`.
- Loại: test tự động + build.
- Lệnh / thao tác:
  - `backend/`: `.venv/Scripts/python -m pytest -q -p no:cacheprovider`.
  - `frontend/`: `npx vitest run`, `npm run build`.
  - `ruff check` cho `app/embeddings` và hai file test mới.
- Kỳ vọng: không lỗi.
- Kết quả thực tế:
  - Backend: `1597 passed, 24 skipped`. Các test bị bỏ qua là do thiếu file dữ liệu D26/benchmark/FAQ thật (thư mục
    `data/` bị gitignore), không liên quan DB.
  - Frontend: `47 files, 399 tests passed`; build `✓ built in 2.44s`.
  - Ruff: `All checks passed!` cho file mới/sửa trong `app/embeddings` và hai file test mới. File cũ như `routes.py`
    vốn đã có lỗi ruff trên `dev`; không đánh giá lại.
  - Sau lượt sửa lint (sắp import, gộp `with`, fixture), chạy lại ba file test profile/API: 104 passed.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra lệnh.

### V-10 — S-06 (logo nhà cung cấp)

- Người thực hiện / thời gian: claude-agent / `2026-11-24T17:50:32+07:00`.
- Loại: test tự động + build + kiểm tra ảnh chụp.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác:
  - `npx vitest run`: `47 files, 399 tests passed`.
  - `npm run build`: `✓ built in 2.36s`.
  - Ảnh chụp Playwright, sáng và tối, với kho giả lập có profile Azure, Gemini (LLM) và Voyage, Cohere, Gemini, Jina,
    BGE-M3 (embedding).
  - Thứ tự: mở `#settings/models-llm` trước rồi sang `#settings/models-embedding`, để panel LLM ẩn chứa bản Gemini
    đầu tiên trong DOM.
- Kỳ vọng: mỗi nhà cung cấp có logo đúng ở lựa chọn trong hộp thoại và hàng danh sách; logo đọc được trên cả hai nền;
  Gemini ở panel embedding vẫn có màu gradient.
- Kết quả thực tế: đạt.
  - Ảnh (scratchpad phiên, `shots/out/`): `logos-embedding-choices-{light,dark}.png`,
    `logos-embedding-list-{light,dark}.png`, `logos-llm-{light,dark}.png`.
  - Ghi nhận: phần xanh đậm của logo Cohere hơi tối trên nền tối nhưng vẫn nhận ra (giữ màu thương hiệu).
- Trạng thái: `passed`.
- Bằng chứng: đầu ra lệnh, ảnh chụp.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy đầu `tests/test_embedding_runtime.py` và `tests/test_safe_embedding_startup.py` lỗi do fake OpenAI không nhận
  `dimensions`, và do test cũ coi `cohere`/`gemini` là "chưa hỗ trợ". Đã cập nhật test theo hành vi mới và chạy lại:
  đạt.
- `not_run`: gọi thật API Voyage/Cohere/Gemini/Jina/Mistral (không có khoá thử). Tên trường dựa trên tài liệu API đã
  biết. Cần bấm "Kiểm tra kết nối" với khoá thật để xác nhận.
- `not_run`: nạp lại toàn bộ tài liệu bằng mô hình mới trên DB thật (đổi embedding cần khởi động lại backend và tốn chi
  phí API).

## Kết luận

- Tiêu chí đã đạt: AC-01 … AC-09 (theo test giả lập và ảnh chụp).
- Tiêu chí chưa đạt/chưa xác minh: không có tiêu chí bắt buộc chưa đạt. Gọi dịch vụ thật chưa chạy (ghi ở trên).
- Đề xuất: bàn giao reviewer.

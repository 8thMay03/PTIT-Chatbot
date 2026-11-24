# Verification: 2026-11-24-reranker-api-providers

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`. Gọi dịch vụ thật là `not_run`, xem cuối file.
- Bản được kiểm tra: working tree nhánh `feat/reranker-api-providers` (tách từ `dev` tại `8d9b134`), sau đó commit
  nguyên trạng thành `c62d938`.
- Môi trường:
  - Windows 11, Python 3.11.5 (`backend/.venv`), Node v24, vitest 3.2.7.
  - Postgres `ptit_chatbot_postgres` (Docker) đang chạy.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-agent / `2026-11-24T18:55:00+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q tests/test_reranker_api_profiles.py`.
- Kỳ vọng:
  - 4 hãng: thiếu khoá thì 422. Có khoá thì 201; khoá không có trong response/DB; Base URL gửi kèm bị bỏ.
  - Chọn profile của hãng: settings đúng provider/model/khoá, không có Base URL.
  - TEI: thiếu Base URL hoặc URL ngoài allowlist thì 422; không khoá vẫn được.
  - Đổi hãng không nhập khoá thì 422; sang TEI thì khoá cũ bị xoá.
- Kết quả thực tế: 13 passed.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra pytest.

### V-02 — AC-02

- Người thực hiện / thời gian: claude-agent / `2026-11-24T18:54:00+07:00`.
- Loại: test tự động (`httpx.post` giả, không gọi mạng).
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q tests/test_reranker.py`.
- Kỳ vọng:
  - URL, header, body từng hãng đúng bảng trong `task.md`.
  - Base URL còn sót trong settings không được dùng cho hãng có URL cố định.
  - Pinecone: `Api-Key` + `X-Pinecone-Api-Version`, đoạn dạng `{text}`.
  - TEI: `{query, texts}`, tự sắp xếp và cắt `top_n`, Base URL ngoài allowlist không gọi.
  - Thiếu khoá thì không gọi và quay về heuristic, log có host.
  - Response sai khoá/trường điểm thì `RerankAPIError`.
- Kết quả thực tế: 30 passed (14 test cũ của `rerank_api` + 16 test mới).
- Trạng thái: `passed`.
- Bằng chứng: đầu ra pytest.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-agent / `2026-11-24T18:55:00+07:00`.
- Loại: test tự động.
- Lệnh / thao tác: `tests/test_reranker_api_profiles.py` (các test `test_test_*`) và `tests/test_model_profiles.py`
  (các test `test_test_reranker_*` cũ).
- Kỳ vọng:
  - Hãng có URL cố định: bỏ `base_url` client gửi, dùng khoá profile cùng hãng.
  - Khoá profile Cohere không dùng khi kiểm tra Voyage (422 nếu không nhập khoá).
  - TEI không khoá được; TEI thiếu Base URL hoặc URL ngoài allowlist thì 422.
- Kết quả thực tế: passed (nằm trong V-01 và V-06).
- Trạng thái: `passed`.

### V-04 — AC-04

- Người thực hiện / thời gian: claude-agent / `2026-11-24T18:54:00+07:00`.
- Loại: test tự động.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q tests/test_retrieval_confidence.py tests/test_config_api.py`.
- Kỳ vọng:
  - `test_rerank_api_uses_override_only_never_cross_encoder_table` đạt với cả 6 provider API.
  - `available_providers.reranker` có đủ 8 provider.
- Kết quả thực tế: passed.
- Trạng thái: `passed`.

### V-05 — AC-05

- Người thực hiện / thời gian: claude-agent / `2026-11-24T18:58:00+07:00`.
- Loại: test tự động + build.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run`; `npm run build`.
- Kỳ vọng:
  - Catalog có 7 provider reranker; quy tắc khoá đúng; payload kiểm tra không gửi Base URL với hãng.
  - Hộp thoại Voyage không có Base URL, bắt buộc khoá, có ghi chú gửi dữ liệu và "Kiểm tra kết nối".
  - Ngưỡng rerank thang 0–1 cho Voyage.
- Kết quả thực tế: 47 file / 403 test passed; build thành công.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra vitest/vite.

### V-06 — AC-06

- Người thực hiện / thời gian: claude-agent / `2026-11-24T18:58:30+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q`.
- Kết quả thực tế: 1631 passed, 24 skipped, 1 warning (StarletteDeprecationWarning có sẵn).
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy đầu `test_config_api.py::test_get_config_returns_full_structure` thất bại.
  - Nguyên nhân: test cũ khẳng định `"cohere" not in available_providers.reranker`, ghi lại quyết định của task
    api-reranker.
  - Đã cập nhật theo danh sách mới; chạy lại passed.
- Lần chạy đầu `pipelineSummary.test.js` thất bại.
  - Nguyên nhân 1: `isApiReranker("toString")` trả `true` vì toán tử `in` đọc cả prototype. Đã sửa bằng `Object.hasOwn`.
  - Nguyên nhân 2: assertion cũ `not.toHaveProperty("cohere")`. Đã gỡ.
  - Chạy lại passed.
- `not_run`: chưa gọi dịch vụ thật (không có khoá Cohere/Jina/Voyage/Pinecone, không có máy chủ TEI).
  - Định dạng request/response đối chiếu tài liệu chính thức ngày 2026-11-24.
  - Riêng tham số tuỳ chọn của TEI lấy từ bản tóm tắt openapi.json; client chỉ dùng `query` và `texts`, hai trường có
    trong ví dụ README.

## Kết luận

- Tiêu chí đã đạt: AC-01..AC-06.
- Tiêu chí chưa xác minh: gọi dịch vụ thật (ngoài AC, đề xuất thử bằng "Kiểm tra kết nối").
- Đề xuất: bàn giao review.

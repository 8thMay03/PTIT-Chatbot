# Verification: 2026-11-24-list-provider-models

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `feat/list-provider-models` (tách từ `dev` tại `25d8a32`) trước commit, gồm
  sửa R-03.
- Môi trường: Windows 11, Python `backend/.venv`, Postgres (Docker) chạy, Node + Vitest 3.2.7, Vite.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-agent / `2026-11-24T22:33:18+07:00`.
- Loại: test tự động (`httpx.get` giả, không gọi mạng thật).
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest tests/test_provider_models.py -q`.
- Kỳ vọng: request/xác thực/lọc đúng cho OpenAI (LLM, embedding), tương thích OpenAI, Gemini (phân trang, lọc theo
  phương thức, khoá trong header không trong URL), Cohere (endpoint, bỏ deprecated), Pinecone, TEI, Rerank API; bỏ
  trùng/rỗng/quá dài; lỗi 401/404/không JSON/sai định dạng/timeout/lỗi kết nối → thông báo không chứa khoá hay body;
  nhà cung cấp không hỗ trợ/thiếu khoá/URL ngoài allowlist → lỗi, không gọi mạng.
- Kết quả thực tế: `23 passed`.
- Trạng thái: `passed`.
- Bằng chứng: các test `test_openai_*`, `test_compatible_*`, `test_gemini_*`, `test_cohere_*`, `test_pinecone_*`,
  `test_tei_*`, `test_cleans_*`, `test_errors_are_safe_messages`, `test_rejects_*`.

### V-02 — AC-02

- Người thực hiện / thời gian: claude-agent / `2026-11-24T22:33:18+07:00`.
- Loại: test tự động qua `TestClient`.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: cùng lệnh V-01 (các test `test_endpoint_*`).
- Kỳ vọng: chưa đăng nhập admin bị từ chối; Azure → 422; URL ngoài allowlist/thiếu Base URL → 422 và không gọi mạng dù
  profile có khoá; khoá profile dùng khi cùng loại + nhà cung cấp, không trả về response; hãng URL cố định bỏ Base URL
  client; khoá Cohere không gửi sang Pinecone; profile khác loại → 422; khoá `.env` chỉ cho OpenAI, không cho tương
  thích OpenAI; lỗi nhà cung cấp → `success=false` và thông báo.
- Kết quả thực tế: nằm trong `23 passed` của V-01.
- Trạng thái: `passed`.
- Bằng chứng: `test_endpoint_requires_admin`, `test_endpoint_checks_url_before_using_stored_key`,
  `test_endpoint_fixed_url_provider_ignores_client_base_url`, `test_endpoint_never_uses_key_of_other_provider_or_kind`,
  `test_endpoint_env_key_fallback_only_for_env_providers`, `test_endpoint_rejects_unsupported_provider`,
  `test_endpoint_reports_upstream_error`.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-agent / `2026-11-24T22:33:18+07:00`.
- Loại: test tự động (Vitest + jsdom) và kiểm tra thủ công bằng ảnh chụp.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run src/models`; chụp hộp thoại bằng playwright-core (API giả lập, Vite dev) ở 1280 px
  sáng và 390 px tối: chọn "Tương thích OpenAI", nhập Base URL, chuyển focus sang ô khoá.
- Kỳ vọng: payload đúng hợp đồng; rời ô trống không gọi; rời ô có giá trị tự tải một lần; ô chọn + chuyển gõ tay giữ
  giá trị và gợi ý; đổi Base URL ẩn danh sách cũ; lỗi hiện cạnh ô (`role=alert`); thiếu Base URL/khoá báo lỗi không gọi
  mạng; một mô hình tự điền; sửa profile gửi `profile_id`; Azure/Cross-Encoder không có nút; bố cục không vỡ.
- Kết quả thực tế: `26 passed` (3 file). Ảnh: nút "Tải lại danh sách" cùng hàng nhãn "Mô hình", ô chọn hiện
  `qwen2.5:7b`, dòng "Đã tải 5 mô hình từ nhà cung cấp." và link "Nhập tên khác"; trên 390 px các trường xếp một cột,
  không tràn ngang.
- Trạng thái: `passed`.
- Bằng chứng: `ModelsView.test.jsx` (3 test mới), `catalog.test.js` ("lấy danh sách mô hình…"); ảnh trong scratchpad
  phiên (không commit).

### V-04 — AC-04

- Người thực hiện / thời gian: claude-agent / `2026-11-24T22:33:18+07:00`.
- Loại: test tự động, build.
- Lệnh / thao tác: `backend/`: `.venv/Scripts/python -m pytest -q -x -p no:cacheprovider`; `frontend/`:
  `npx vitest run`, `npx vite build`.
- Kỳ vọng: không lỗi.
- Kết quả thực tế: backend `1654 passed, 24 skipped`; frontend `47 files, 407 passed` (chạy lại sau sửa R-03, vẫn
  `407 passed`); build `✓ built`.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra lệnh trong phiên.

### V-05 — AC-05

- Người thực hiện / thời gian: claude-agent / `2026-11-24T22:44:10+07:00`.
- Loại: test tự động, build, kiểm tra thủ công bằng ảnh chụp.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run`; `npx vite build`; chụp hộp thoại thêm LLM (tương thích OpenAI, đã tải danh sách) ở
  1280 px sáng và 390 px tối.
- Kỳ vọng: hộp thoại thêm mới không có mô tả đầu, mô tả thẻ nhà cung cấp, gợi ý ô khoá; test cũ sửa theo nội dung mới
  vẫn qua; bố cục thẻ nhà cung cấp một dòng không vỡ.
- Kết quả thực tế: `47 files, 407 passed`; build `✓ built`. Ảnh: tiêu đề hộp thoại không có dòng mô tả, thẻ nhà cung cấp
  chỉ có biểu tượng + tên, dưới ô mô hình chỉ còn link "Nhập tên khác", dưới ô khoá không còn chữ.
- Trạng thái: `passed`.
- Bằng chứng: test "thêm LLM qua hộp thoại…" kiểm `.mdl-dialog-heading p`, `.mdl-choice-text span`,
  `#mdl-llm-form-key-hint` không tồn tại; ảnh trong scratchpad phiên (không commit).
- Chạy lại `2026-11-24T22:47:51+07:00` sau khi bỏ placeholder: `npx vitest run` → `47 files, 407 passed`; `npx vite build` → `✓ built`; test
  "thêm LLM qua hộp thoại…" kiểm ô mô hình và ô khoá không có thuộc tính `placeholder`.
- Chạy lại `2026-11-24T22:49:13+07:00` sau khi bỏ nhãn khoá `.env`: `npx vitest run` → `47 files, 407 passed`; `npx vite build` → `✓ built`;
  test "thêm LLM qua hộp thoại…" kiểm hộp thoại OpenAI không chứa ".env" và hiện "Không bắt buộc".
- Chạy lại `2026-11-24T22:50:49+07:00` sau khi dọn Azure: `npx vitest run` → `47 files, 407 passed`; `npx vite build` → `✓ built`; test "sửa
  profile: …Azure không có nút tải" kiểm 4 ô Azure không có `placeholder` và không còn `.mdl-field-hint`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Chưa gọi API thật của OpenAI/Gemini/Cohere/Pinecone/TEI/Ollama (không có khoá/máy chủ trong phiên); định dạng dựa
  trên tài liệu chính thức đã đối chiếu 2026-11-24 (trường `model_id` của TEI `/info` chưa đối chiếu được trang tài
  liệu, dựa trên định nghĩa đã biết của TEI).
- `ruff check` các file mới: sạch. File đã có: thêm một B008 (`Depends` trong tham số mặc định) giống mọi route khác.
  Repo không áp `ruff format` và frontend không có cấu hình ESLint.

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-02, AC-03, AC-04, AC-05.
- Tiêu chí chưa đạt/chưa xác minh: không có (gọi API thật ghi ở trên, ngoài AC).
- Đề xuất: review và mở PR.

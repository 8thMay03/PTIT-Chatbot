# Verification: 2026-10-13-models-view-redesign

- Verifier: `claude`.
- Trạng thái tổng: `passed` (trừ V-08 `not_run`).
- Bản được kiểm tra: working tree trên base `79dae24` với thay đổi ở `frontend/src/ModelsView.jsx`, `frontend/src/styles/models.css`, `frontend/src/styles/components.css`.
- Môi trường: Linux container, Node v22.22.0, Vite 5 dev server, Chromium (Playwright 1.56) headless; API giả lập bằng `page.route` (không có backend thật).

## Kiểm chứng tiêu chí

Script kiểm tra trình duyệt: `verify-models.mjs` (đặt ngoài repo, trong scratchpad của phiên). Script chạy Vite với `VITE_API_BASE_URL=http://mock.local/api`, chặn request, mô phỏng `PUT /config` theo logic `update_runtime_config` và ghi lại payload gửi đi. Kết quả lần chạy cuối: `28/28 passed`.

### V-01 — AC-01

- Người thực hiện / thời gian: claude / `2026-10-14T00:36:10+07:00`.
- Loại: kiểm tra trình duyệt tự động.
- Thao tác: mở `#settings/models`, đếm `.mdl-card`, tìm chuỗi VLM/ASR/TTS/OCR trong nội dung.
- Kỳ vọng: đúng 3 mục, không có các loại mô hình backend không hỗ trợ.
- Kết quả thực tế: PASS "chỉ có 3 mục", PASS "không còn VLM/ASR/TTS/OCR".
- Trạng thái: `passed`.

### V-02 — AC-02

- Loại: kiểm tra trình duyệt tự động.
- Thao tác và kết quả:
  - Chọn "Tương thích OpenAI" → "Ollama" → "Kiểm tra kết nối": payload `{"provider":"openai_compatible","model":"qwen2.5:7b","api_key":null,"base_url":"http://localhost:11434/v1","endpoint":null,"deployment_name":null,"api_version":null}`; khối "Kết nối thành công" hiện thời gian phản hồi và câu trả lời mẫu. PASS.
  - "Lưu": payload `{"llm":{"provider":"openai_compatible","openai_compatible_base_url":"http://localhost:11434/v1","openai_compatible_model":"qwen2.5:7b"}}`; nút Lưu tắt lại, tiêu đề đổi thành "Đang dùng qwen2.5:7b · Tương thích OpenAI". PASS.
  - Chọn Azure để trống rồi Lưu: không có request, hiện lỗi tại ô, focus vào `#llm-azure-endpoint`. PASS.
  - Lưu tắt khi chưa có thay đổi. PASS.
  - Phím mũi tên trên radio đổi nhà cung cấp. PASS.
- Trạng thái: `passed`.

### V-03 — AC-03

- Thao tác: chọn OpenAI, nhập key `sk-test-123456`, Lưu.
- Kết quả: ô nhập là `type=password`; payload `{"llm":{"provider":"openai","openai_model":"gpt-4.1-mini","openai_api_key":"sk-test-123456"}}` (không gửi base URL chưa sửa); ô key trống sau khi lưu; `localStorage` không chứa key; khoá cũ `ptit_added_providers` đã bị xoá. Payload ở V-02 không có trường key khi người dùng không nhập.
- Trạng thái: `passed`.

### V-04 — AC-04

- Kết quả: mục Embedding không có nút Lưu (PASS); ảnh `m07-embedding`, `m12-dark-reranker` cho thấy giải thích, các bước đổi qua `.env` và nút "Chép".
- Trạng thái: `passed`.

### V-05 — AC-05

- Kết quả: chọn Cross-Encoder, nhập `BAAI/bge-reranker-base`, Lưu → payload `{"reranker":{"provider":"cross-encoder","model":"BAAI/bge-reranker-base"}}` (PASS). Bản nháp LLM đang sửa (`gpt-4o`) vẫn còn sau khi lưu reranker (PASS). Cấu hình `reranker.enabled=false` hiện nhãn "Đang tắt" + cảnh báo; bấm "Bật trong Cấu hình RAG" chuyển sang tab Cấu hình RAG (PASS).
- Trạng thái: `passed`.

### V-06 — AC-06

- Kết quả:
  - Không tràn ngang ở 1440px và 390px (ba vị trí cuộn): `scrollWidth - clientWidth ≤ 0`. PASS.
  - Chế độ tối: ảnh `m10`, `m11`, `m12`; không có lỗi JS. PASS.
  - Lỗi tải (API ngắt kết nối): hiện khối "Không đọc được cấu hình mô hình", không hiện form; "Thử lại" tải lại được 3 mục. PASS.
  - Radio thật (`input type=radio`), nút thật; không còn `div` có `onClick`.
- Trạng thái: `passed`.

### V-07 — AC-07 và hồi quy

- Thư mục chạy: `frontend/`.
- Lệnh: `npm run build`.
- Kết quả thực tế: `✓ built` không lỗi.
- Hồi quy do sửa `components.css`: chụp hộp thoại chọn parser, xoá tài liệu, khôi phục cấu hình ở chế độ sáng/tối; nút Hủy/Xóa/Khôi phục hiển thị đúng.
- Kiểm tra màu cứng: `grep` không thấy hex/rgba trong `models.css`.
- Trạng thái: `passed`.

### V-08 — Backend thật

- Thao tác: chạy với FastAPI + nhà cung cấp LLM thật.
- Trạng thái: `not_run` — môi trường không có backend/khoá API. Hợp đồng payload đã đối chiếu với `UpdateConfigRequest`, `TestLLMRequest` và `update_runtime_config`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Ảnh `m06` từng cho thấy thẻ Heuristic còn viền đỏ sau khi chọn Cross-Encoder; tái hiện riêng và đo style tính toán sau 600ms cho kết quả đúng (chỉ thẻ được chọn mang `is-selected`) → ảnh chụp giữa hiệu ứng chuyển màu 120ms, không phải lỗi.
- Phát hiện icon trong `inline-alert` bị co nhỏ → thêm `flex-shrink: 0`, chạy lại V-01 → V-07: 28/28 passed.

## Kết luận

- Tiêu chí đã đạt: AC-01 → AC-07.
- Chưa xác minh: hành vi với backend thật (V-08).
- Đề xuất: bàn giao reviewer.

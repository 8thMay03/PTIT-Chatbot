# Task: Thiết kế lại màn Settings → Mô hình

- ID: `2026-10-13-models-view-redesign`
- Trạng thái: `done`
- Coordinator: `claude`
- Người yêu cầu: chủ repo (qua phiên Claude Code)
- Tạo lúc: `2026-10-14T00:29:27+07:00`
- Cập nhật lúc: `2026-10-14T00:36:10+07:00`

## Yêu cầu và kết quả mong muốn

Người dùng yêu cầu redesign màn "Model provider" (Settings → Mô hình) sau đợt rà soát UI/UX.

Hành vi hiện tại:

- Màn mô phỏng một "marketplace" nhà cung cấp viết cứng (OpenAI, Gemini, Qwen, Cohere, Ollama) với các ô VLM/ASR/TTS/OCR mà backend không có.
- Chọn mô hình cho VLM/ASR/TTS gửi `PUT /config` rỗng nhưng vẫn báo thành công; nút ✕ ở Embedding/Rerank chỉ xoá trên giao diện.
- Hộp thoại "Cấu hình nhà cung cấp" không có CSS (class `form-*`, `btn-primary`, `btn-ghost`... chưa định nghĩa), không đóng bằng Esc, không giữ focus.
- Thẻ nhà cung cấp và ô chọn mô hình là `div` có `onClick`, không dùng được bằng bàn phím; ô chọn tràn màn hình trên mobile.
- Đổi Embedding qua API không có tác dụng vì `Retriever`/`IngestionPipeline` tạo mô hình nhúng một lần khi khởi động.

Kết quả cần có: màn hình chỉ thể hiện đúng ba vai trò backend thật sự dùng (LLM, Embedding, Reranker), thao tác lưu/kiểm tra có tác dụng thật, trung thực về giới hạn của cấu hình runtime.

## Phạm vi

- Bao gồm: `frontend/src/ModelsView.jsx`, `frontend/src/styles/models.css`, sửa selector thiếu dấu phẩy và chuyển class dùng chung trong `frontend/src/styles/components.css`.
- Ngoài phạm vi: thay đổi API backend; lưu cấu hình xuống `.env`; các màn khác (Cấu hình RAG, Dataset, Chat).
- Ràng buộc: dùng hợp đồng `GET/PUT /api/config`, `POST /api/config/test-llm` hiện có; chỉ dùng token màu trong `tokens.css`; không lưu API key trong trình duyệt.

## Tiêu chí nghiệm thu

- [x] AC-01: Màn chỉ có ba mục LLM, Embedding, Reranker; không còn VLM/ASR/TTS/OCR hay danh mục nhà cung cấp giả.
- [x] AC-02: Mục LLM cho chọn OpenAI / Gemini / Azure OpenAI / Tương thích OpenAI với đúng các trường backend nhận; "Lưu" gửi `PUT /config` đúng payload, chỉ bật khi có thay đổi hợp lệ; "Kiểm tra kết nối" gọi `POST /config/test-llm` và hiển thị kết quả.
- [x] AC-03: API key không bao giờ hiển thị hay lưu trong trình duyệt; trạng thái "đã có khoá" lấy từ máy chủ; để trống thì giữ khoá cũ.
- [x] AC-04: Mục Embedding chỉ hiển thị cấu hình đang chạy và hướng dẫn đổi qua `.env` (không có nút lưu giả).
- [x] AC-05: Mục Reranker cho chọn heuristic / cross-encoder (+ tên mô hình) và lưu thật; hiện trạng thái bật/tắt kèm đường dẫn sang Cấu hình RAG.
- [x] AC-06: Dùng được bằng bàn phím (radio thật, nút thật), hiển thị đúng ở chế độ sáng/tối, 1440px và 390px không tràn ngang; có trạng thái đang tải và lỗi tải có nút thử lại.
- [x] AC-07: `npm run build` thành công.

## Tài liệu và phụ thuộc

- `backend/app/api/schemas.py` (`UpdateConfigRequest`, `TestLLMRequest`), `backend/app/core/config.py` (`update_runtime_config`, `get_runtime_config_dict`).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: AC-01 → AC-07 đạt (`verification.md` V-01 → V-07); self_review `approved`. Chưa chạy với backend thật (V-08 `not_run`).
- Blocker: không có.
- Bước tiếp theo: người yêu cầu kiểm tra với backend thật; theo dõi R-01 → R-03 (low, deferred).

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-10-14T00:29:27+07:00 — claude: tạo task, chuyển `in_progress`. Quyết định Embedding chỉ đọc vì backend không áp dụng thay đổi runtime cho mô hình nhúng.
- 2026-10-14T00:36:10+07:00 — claude: S-01, S-02 hoàn tất, review approved → `done`.

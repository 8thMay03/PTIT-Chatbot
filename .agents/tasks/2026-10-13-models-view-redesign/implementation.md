# Implementation: 2026-10-13-models-view-redesign

## Tổng quan triển khai

S-01 đã tích hợp trên working tree của nhánh `claude/great-wright-hsghxd` (base `79dae24`). Không thay đổi backend.

## Nhật ký theo nhiệm vụ

### S-01 — claude

- Cập nhật lúc: `2026-10-14T00:36:10+07:00`.
- Đã làm:
  - Viết lại `ModelsView.jsx` thành ba mục xếp dọc, mỗi mục tự lưu:
    - **Sinh câu trả lời (LLM)**: radio dạng thẻ chọn OpenAI / Google Gemini / Azure OpenAI / Tương thích OpenAI; mỗi nhà cung cấp chỉ hiện các trường backend nhận (`LLM_FIELDS`). Nút điền nhanh base URL cho Ollama, vLLM, DeepSeek, Qwen (giá trị lấy từ `PROVIDER_DEFAULT_BASE_URLS` của backend). Ô API key dạng password + nút hiện/ẩn, nhãn "Máy chủ đã có khoá / Chưa có khoá" lấy từ cờ `*_has_key`; để trống thì giữ khoá cũ. "Kiểm tra kết nối" gọi `POST /config/test-llm` và hiển thị thời gian phản hồi + câu trả lời mẫu. "Lưu" chỉ gửi các trường của nhà cung cấp đang chọn; base URL OpenAI chỉ gửi khi người dùng sửa (máy chủ không trả giá trị này khi OpenAI không phải nhà cung cấp đang dùng). Thiếu trường bắt buộc / URL sai thì báo lỗi tại ô và đưa focus vào ô đầu tiên, không gửi request.
    - **Xếp hạng lại (Reranker)**: chọn Heuristic / Cross-Encoder (+ tên mô hình, có gợi ý). Hiện trạng thái bật/tắt; nếu đang tắt có liên kết sang tab Cấu hình RAG. Không gửi `enabled` để không giành quyền với màn Cấu hình RAG.
    - **Nhúng văn bản (Embedding)**: chỉ đọc. Giải thích vì sao không đổi tại đây (mô hình nạp một lần khi khởi động, `retriever.py:16`, `pipeline.py:33`) và các bước đổi qua `.env` + nút chép cấu hình hiện tại.
  - Banner nói rõ cấu hình chỉ áp dụng cho tiến trình đang chạy, không ghi `.env`.
  - Trạng thái đang tải; lỗi tải hiển thị khối lỗi + "Thử lại" thay vì form chứa giá trị mặc định giả.
  - Mỗi mục chỉ nhận phần cấu hình của mình (so sánh qua JSON) nên lưu Reranker không xoá bản nháp LLM.
  - Cảnh báo `beforeunload` khi còn thay đổi chưa lưu (giống màn Cấu hình RAG).
  - Xoá khoá localStorage cũ `ptit_added_providers` của màn trước.
  - Viết lại `models.css` (tiền tố `mdl-`), chỉ dùng token màu.
  - `components.css`: sửa ba selector thiếu dấu phẩy (`.ghost-btn .danger-btn` bị hiểu thành selector con cháu nên kiểu nền của hai nút này chưa từng được áp dụng); chuyển `.model-mgmt-loading`, `.model-mgmt-spinner`, `.search-clear-btn` từ `models.css` sang đây vì Cấu hình RAG, Dataset, Tài liệu đang dùng.
- File thay đổi: `frontend/src/ModelsView.jsx`, `frontend/src/styles/models.css`, `frontend/src/styles/components.css`; commit: xem lịch sử nhánh.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: các nút `.ghost-btn`/`.danger-btn` trên toàn ứng dụng nay nhận đúng padding/kiểu chữ; đã chụp kiểm tra hộp thoại parser, xoá tài liệu, khôi phục cấu hình (V-07).
- Kiểm tra đã chạy: xem `verification.md` V-01 → V-07.
- Còn lại/blocker: không có blocker. Các điểm hoãn ghi trong `review.md`.

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

### HANDOFF-claude-001 — S-01

- Từ / đến: `claude` / người yêu cầu.
- Đã hoàn tất: S-01, S-02.
- File/branch/commit/patch: nhánh `claude/great-wright-hsghxd`.
- Kiểm chứng: `verification.md` — passed, trừ kiểm tra với backend thật (`not_run`).
- Review: `review.md` — `approved` (self_review), không còn nhận xét bắt buộc.
- Hạn chế / còn lại: R-01 → R-03 (low, deferred).
- Bước tiếp theo: người yêu cầu kiểm tra với backend thật.

# Implementation: 2026-11-24-list-provider-models

## Tổng quan triển khai

S-01 và S-02 đã tích hợp trên nhánh `feat/list-provider-models` (tách từ `dev` tại `25d8a32`).

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-11-24T22:33:18+07:00`.
- Đã làm:
  - `app/core/provider_models.py` (mới): `list_models(kind, provider, api_key, base_url)` gọi `httpx.get` (timeout
    10 s, không theo redirect) theo bảng trong `task.md`; Gemini/Cohere theo trang (tối đa 5 trang); lọc theo loại;
    `_clean` bỏ trùng/rỗng/>255 ký tự, sắp xếp không phân biệt hoa thường, tối đa 1000. `ModelListError.reason` chỉ gồm
    mã HTTP/tên lớp lỗi; `error_message` thêm gợi ý theo mã (401/403/404/429). Base URL do admin nhập được kiểm lại
    allowlist ngay trong module.
  - `model_profiles.resolve_list_models_key`: nhập tay > khoá profile cùng loại, cùng nhà cung cấp > khoá `.env` (LLM
    OpenAI/Gemini, embedding OpenAI — giống mô hình đang chạy). Profile khác loại → `ConfigValidationError` (422).
  - `routes.list_provider_models` (`POST /model-profiles/list-models`): kiểm hỗ trợ, bỏ Base URL với hãng URL cố định,
    kiểm allowlist trước khi lấy khoá; lỗi nhà cung cấp trả `success=false` kèm thông báo; danh sách rỗng trả thông báo.
  - `schemas`: `ListProviderModelsRequest`, `ListProviderModelsResponse`.
- File thay đổi: như phạm vi S-01 trong `plan.md`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: hợp đồng endpoint trong `plan.md`.
- Kiểm tra đã chạy: V-01, V-02, V-04.
- Còn lại/blocker: không có.

### S-02 — claude-agent

- Cập nhật lúc: `2026-11-24T22:33:18+07:00`.
- Đã làm:
  - `api/modelProfiles.js`: `listModels(payload)`.
  - `catalog.js`: `MODEL_LIST_BASE_URL`, `canListModels`, `listModelsBlocker` (thiếu/sai Base URL, thiếu khoá bắt
    buộc), `modelListSignature` (kind, provider, Base URL, khoá, cờ xoá khoá), `buildListModelsPayload` (không gửi Base
    URL với hãng URL cố định; "Xoá khoá đã lưu" thì không gửi `profile_id`).
  - `fields.jsx`: `ModelField` — nút "Tải danh sách"/"Tải lại danh sách" trên hàng nhãn; có danh sách thì `<select>`
    (giá trị hiện tại không có trong danh sách vẫn giữ, ghi "(không có trong danh sách)"), link "Nhập tên khác"/"Chọn
    trong danh sách (N)"; ô gõ tay dùng datalist gồm mô hình đã tải + gợi ý có sẵn; trạng thái tải/lỗi/số mô hình.
    `TextField`, `ApiKeyField` nhận thêm `onBlur`.
  - `ModelKindPanel.jsx`: tách `applyDraftChange` (dùng chung cho cập nhật thường và tự điền); `loadModels` với id
    request để bỏ kết quả cũ, chỉ hiện danh sách khi chữ ký khớp cấu hình hiện tại; rời ô Base URL/khoá có giá trị thì
    tự tải (bỏ qua im lặng nếu thiếu thông tin hoặc đã tải); một mô hình thì tự điền khi ô trống và cấu hình chưa đổi.
  - `models.css`: nút trên hàng nhãn không có margin-top; style `select.mdl-input`.
- File thay đổi: như phạm vi S-02 trong `plan.md`.
- Kiểm tra đã chạy: V-03, V-04.
- Còn lại/blocker: không có.

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

### HANDOFF-claude-agent-001 — S-01, S-02

- Từ / đến: `claude-agent` / người dùng.
- Đã hoàn tất: AC-01..AC-04.
- File/branch/commit/patch: nhánh `feat/list-provider-models`.
- Kiểm chứng: `verification.md` — `passed`.
- Review: `review.md` — `approved` (self_review); R-01, R-02 deferred, R-03 resolved.
- Hạn chế / còn lại: chưa thử với khoá thật của từng hãng.
- Bước tiếp theo: push, mở PR vào `dev`, thử thực tế với Ollama/OpenAI/Gemini/Cohere/Pinecone.

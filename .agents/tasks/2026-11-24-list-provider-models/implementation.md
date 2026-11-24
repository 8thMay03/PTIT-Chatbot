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

### S-03 — claude-agent

- Cập nhật lúc: `2026-11-24T22:44:10+07:00`.
- Đã làm (tiêu chí: giữ cảnh báo/lỗi và gợi ý tránh lỗi cấu hình mà admin không tự thấy; bỏ phần giải thích điều hiển nhiên):
  - `catalog.js`: bỏ `description` của mọi nhà cung cấp; bỏ 15 gợi ý trường (Base URL OpenAI, Sentence-Transformers,
    Cross-Encoder, số chiều Voyage/Cohere/Gemini/Jina/tương thích, Base URL tương thích/Rerank API/TEI về allowlist —
    lỗi allowlist đã hiện khi lưu/kiểm tra, câu "quá 8 giây thì dùng heuristic" lặp ở mọi reranker). Giữ: tên deployment
    Azure ≠ tên mô hình; giới hạn 100 đoạn của Pinecone và 32 đoạn của TEI (vượt thì âm thầm rơi về heuristic), đã rút
    gọn. Bỏ `sendsDocumentsToService` (không còn dùng).
  - `fields.jsx`: thẻ nhà cung cấp chỉ còn tên; bỏ gợi ý "Khoá được mã hoá…" của ô khoá; `ModelField` bỏ dòng "Đang lấy
    danh sách…"/"Đã tải N mô hình…" (nút và ô chọn đã thể hiện), rút gọn lỗi thành "Không tải được danh sách: …", bỏ
    hậu tố "(không có trong danh sách)".
  - `ModelKindPanel.jsx`: bỏ mô tả đầu hộp thoại khi thêm mới/sửa mô hình không dùng; còn khi sửa mô hình đang dùng
    ("lưu xong áp dụng ngay" / embedding "có hiệu lực sau khi khởi động lại backend"). Bỏ gợi ý tên hiển thị, ghi chú
    "…được gửi tới dịch vụ này", ghi chú đệm 0; giữ cảnh báo số chiều lớn hơn `VECTOR_DIM`. Bỏ nhánh một nhà cung cấp
    (mọi loại đều có nhiều nhà cung cấp; nhánh này đọc `description`).
  - `models.css`: bỏ `.mdl-provider-note` và style dòng mô tả thẻ nhà cung cấp.
  - Giữ nguyên các hộp thoại xác nhận (xoá mô hình, đổi embedding): mô tả nêu hệ quả không hoàn tác/cần nạp lại.
- Kiểm tra đã chạy: V-05.
- Bổ sung `2026-11-24T22:47:51+07:00` (yêu cầu người dùng): bỏ placeholder của ô Endpoint (Azure), mọi ô Mô hình và ô API key (gồm
  "Để trống để giữ khoá đã lưu"/"Để trống để dùng … .env" — nhãn trạng thái cạnh ô khoá vẫn báo điều này). Giữ
  placeholder của Base URL, Tên deployment, API version, Số chiều, Tên hiển thị.
- Bổ sung `2026-11-24T22:49:13+07:00` (yêu cầu người dùng): bỏ nhãn "Dùng OPENAI_API_KEY/GEMINI_API_KEY/AZURE_OPENAI_API_KEY trong .env nếu
  để trống" và "Dùng OPENAI_API_KEY đang chạy nếu để trống" cạnh ô khoá; nhà cung cấp dự phòng khoá `.env` giờ hiện
  "Không bắt buộc" như các ô khoá tuỳ chọn khác. Bỏ `ENV_KEY_LABELS`, prop `envFallback`/`envKeyLabel` của `ApiKeyField`
  (`KEY_RULES.envFallback` trong catalog giữ nguyên, mô tả hành vi máy chủ).
- Bổ sung `2026-11-24T22:50:49+07:00` (yêu cầu người dùng): Azure OpenAI bỏ gợi ý "Tên deployment đã tạo trên Azure, không phải tên mô hình
  gốc." và placeholder của Tên deployment, API version (Endpoint đã bỏ trước đó). Giá trị mặc định `2024-02-15-preview`
  điền sẵn vào ô API version khi thêm mới (`emptyDraft`) giữ nguyên — đó là giá trị, không phải placeholder.
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

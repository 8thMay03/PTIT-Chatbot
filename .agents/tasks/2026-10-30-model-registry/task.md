# Task: Kho mô hình LLM / Embedding / Rerank và chọn mô hình đang dùng

- ID: `2026-10-30-model-registry`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-10-30T09:00:00+07:00`
- Cập nhật lúc: `2026-10-30T22:50:00+07:00`

## Yêu cầu và kết quả mong muốn

Tab "Mô hình" trong Settings hiện là một trang gồm ba khối (LLM sửa trực tiếp trường settings,
Reranker chọn heuristic/cross-encoder, Embedding chỉ đọc). Người yêu cầu muốn chia thành ba tab
riêng: **LLM model**, **Embedding model**, **Rerank model**. Mỗi tab cho phép nhập (thêm/sửa/xoá)
nhiều cấu hình mô hình; khi cấu hình mô hình cho hệ thống thì chọn từ những mô hình đã cấu hình.

Người yêu cầu đã chốt (2026-10-30):

- Làm luôn phần chọn mô hình đang dùng từ kho. LLM và Rerank áp dụng ngay.
- Embedding: lưu lựa chọn, có hiệu lực sau khi backend khởi động lại; cảnh báo phải "Nạp lại toàn
  bộ"; chặn khi số chiều khác `VECTOR_DIM`.
- Chỉ hỗ trợ nhà cung cấp backend đang có: LLM (OpenAI, Gemini, Azure OpenAI, tương thích OpenAI),
  Embedding (OpenAI, Sentence-Transformers), Rerank (Cross-Encoder cục bộ; Heuristic có sẵn).

## Phạm vi

- Bao gồm: bảng `model_profiles` + migration, API CRUD/kích hoạt/kiểm tra, áp profile đang chọn
  lúc khởi động, UI ba tab con, test backend + frontend.
- Ngoài phạm vi: nhà cung cấp mới (Cohere, Jina…); kiểm tra kết nối cho embedding/rerank; script
  CLI (`scripts/ingest.py`…) đọc profile embedding đã chọn; đồng bộ nhiều worker.
- Ràng buộc: API key trong profile chỉ lưu dạng bản mã (Fernet, `CONFIG_ENCRYPTION_KEY`), không trả
  về client; URL qua `LLM_BASE_URL_ALLOWLIST`; mọi route admin cần `require_admin`; lỗi giữ nguyên
  cấu hình đang chạy.

## Tiêu chí nghiệm thu

- [x] AC-01: Tab Mô hình có ba tab con LLM model / Embedding model / Rerank model; mỗi tab liệt kê
  các mô hình đã cấu hình của loại đó, cho thêm/sửa/xoá.
- [x] AC-02: Profile lưu bền trong Postgres; API key chỉ ở dạng bản mã, response chỉ có
  `has_api_key`; thiếu khoá mã hoá thì từ chối lưu key (422) và không ghi gì.
- [x] AC-03: Chọn profile LLM / Rerank làm mô hình đang dùng có hiệu lực ngay và còn sau restart;
  sửa profile đang dùng thì áp lại ngay; không xoá được profile đang dùng (409). Có lựa chọn quay
  về cấu hình `.env` (LLM, Embedding) / Heuristic (Rerank).
- [x] AC-04: Chọn profile Embedding được lưu và áp khi backend khởi động lại (embedder tạo lại lúc
  khởi động); số chiều khác `VECTOR_DIM` bị từ chối (422); UI báo "chờ khởi động lại" và nhắc nạp
  lại toàn bộ.
- [x] AC-05: Validate theo nhà cung cấp (trường bắt buộc, URL trong allowlist, tên trùng trong cùng
  loại → 409); kiểm tra kết nối LLM dùng được với khoá đã lưu của profile.
- [x] AC-06: Không hồi quy test backend/frontend hiện có; build frontend thành công.

## Tài liệu và phụ thuộc

- `.agents/tasks/2026-10-28-persist-runtime-config/` (config_store, mã hoá Fernet).
- `.agents/tasks/2026-10-27-fe06-admin-separation/` (allowlist URL, `require_admin`).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: hoàn tất; mọi AC có bằng chứng, self-review approved; người yêu cầu cho merge vào `dev`.
- Blocker: không có.
- Bước tiếp theo: không có (R-02, R-03 deferred — xem review.md).

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-10-30T09:00:00+07:00 — claude-agent: người yêu cầu chọn làm luôn phần chọn mô hình, embedding
  áp dụng sau restart, chỉ dùng provider backend có sẵn.
- 2026-10-30T22:50:00+07:00 — claude-agent: người yêu cầu yêu cầu merge `feat/model-registry` vào `dev`; task `done`.

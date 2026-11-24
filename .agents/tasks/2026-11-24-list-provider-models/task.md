# Task: Lấy danh sách mô hình khả dụng từ nhà cung cấp trong hộp thoại "Thêm mô hình"

- ID: `2026-11-24-list-provider-models`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("chỉ cần nhập base url và api key thì sẽ hiện ra list mô hình khả dụng" → "triển khai đi")
- Tạo lúc: `2026-11-24T22:33:18+07:00`
- Cập nhật lúc: `2026-11-24T22:33:18+07:00`

## Yêu cầu và kết quả mong muốn

Ô "Mô hình" trong hộp thoại thêm/sửa mô hình (Cài đặt → Mô hình) chỉ là ô gõ tự do với vài gợi ý cố định
(`suggestions` trong `frontend/src/models/catalog.js`). Admin phải tự nhớ tên mô hình, nhất là với máy chủ tự host
(Ollama, vLLM…). Cần: nhập Base URL/API key là lấy được danh sách mô hình khả dụng từ nhà cung cấp và chọn trong đó.

**Hiện trạng** (nhánh `dev` tại `25d8a32`): không có endpoint nào hỏi nhà cung cấp danh sách mô hình; đã có các endpoint
"Kiểm tra kết nối" (`/model-profiles/test-*`) với quy tắc: kiểm Base URL qua allowlist trước khi lấy khoá, khoá profile
chỉ dùng khi cùng nhà cung cấp, hãng có URL cố định bỏ Base URL client gửi.

API liệt kê mô hình đã đối chiếu tài liệu chính thức (2026-11-24):

| Nhà cung cấp | Endpoint | Xác thực | Lọc |
|---|---|---|---|
| OpenAI / tương thích OpenAI / Rerank API | `GET {base_url}/models` → `data[].id` | `Authorization: Bearer` | LLM: bỏ tên embedding/tts/whisper/image…; embedding OpenAI: chỉ tên có `embed` |
| Gemini | `GET /v1beta/models?pageSize=1000` → `models[].name`, `nextPageToken` | `x-goog-api-key` | `supportedGenerationMethods` có `generateContent` / `embedContent` |
| Cohere | `GET https://api.cohere.com/v1/models?endpoint=embed\|rerank&page_size=1000` → `models[].name`, `next_page_token` | `Authorization: Bearer` | theo `endpoint`, bỏ `is_deprecated` |
| Pinecone | `GET https://api.pinecone.io/models?type=rerank` → `models[].model` | `Api-Key` + `X-Pinecone-Api-Version` | `type=rerank` |
| HF TEI | `GET {base_url}/info` → `model_id` | `Authorization: Bearer` (tuỳ chọn) | một mô hình |

Không hỗ trợ: Azure OpenAI (khoá data-plane không liệt kê deployment), Voyage, Jina (không có API liệt kê),
Sentence-Transformers/Cross-Encoder chạy cục bộ. Các nhà cung cấp này giữ cách nhập hiện tại.

## Phạm vi

- Bao gồm: module backend lấy danh sách theo nhà cung cấp, endpoint `POST /api/model-profiles/list-models`, cách chọn
  khoá, ô "Mô hình" có nút tải/ô chọn/chuyển sang gõ tay, tự tải khi rời ô Base URL/khoá, test backend và frontend.
- Ngoài phạm vi: tự lấy số chiều vector của mô hình nhúng (vẫn dùng `KNOWN_EMBEDDING_DIMENSIONS` và "Kiểm tra kết
  nối"); lưu cache danh sách; đổi thứ tự trường trong hộp thoại.
- Ràng buộc: khoá không bao giờ gửi tới host ngoài allowlist hoặc tới nhà cung cấp khác; không trả khoá hay response thô
  về client; danh sách chỉ là gợi ý, luôn gõ tay được.

## Tiêu chí nghiệm thu

- [x] AC-01: Backend lấy được danh sách cho mọi (loại, nhà cung cấp) trong bảng trên, đúng request/xác thực, lọc theo
  loại, bỏ trùng/rỗng/quá dài, sắp xếp; lỗi HTTP/mạng/timeout/định dạng → thông báo an toàn, không chứa khoá hay body.
- [x] AC-02: `POST /api/model-profiles/list-models` chỉ cho admin; nhà cung cấp không hỗ trợ → 422; Base URL qua allowlist
  trước khi lấy khoá; hãng URL cố định bỏ Base URL client gửi; khoá: nhập tay > profile cùng loại và cùng nhà cung cấp >
  khoá `.env` (chỉ LLM OpenAI/Gemini, embedding OpenAI); thiếu khoá bắt buộc → báo lỗi, không gọi mạng.
- [x] AC-03: UI: ô "Mô hình" của nhà cung cấp hỗ trợ có nút "Tải danh sách"; tải xong hiện ô chọn, chuyển qua lại với ô
  gõ tay (gợi ý gồm mô hình đã tải); rời ô Base URL/khoá có giá trị thì tự tải một lần cho mỗi cấu hình; đổi
  provider/Base URL/khoá thì ẩn danh sách cũ; lỗi hiện cạnh ô; máy chủ chỉ có một mô hình thì tự điền; nhà cung cấp
  không hỗ trợ không có nút.
- [x] AC-04: Toàn bộ test backend và frontend qua; build frontend qua.
- [x] AC-05 (bổ sung): Hộp thoại thêm/sửa mô hình bỏ mô tả không cần thiết: mô tả nhà cung cấp, gợi ý ô khoá, gợi ý tên
  hiển thị, mô tả đầu hộp thoại (trừ khi sửa mô hình đang dùng), ghi chú gửi dữ liệu, ghi chú đệm 0, gợi ý trường chỉ giải
  thích điều hiển nhiên, dòng "Đã tải N mô hình". Giữ cảnh báo/lỗi và gợi ý tránh lỗi cấu hình không tự thấy được.

## Tài liệu và phụ thuộc

- `.agents/tasks/2026-11-24-embedding-api-providers/`, `.agents/tasks/2026-11-24-reranker-api-providers/`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01, S-02 xong; verification `passed`; review `approved` (self_review; R-01, R-02 deferred; R-03 resolved).
  Mã ở nhánh `feat/list-provider-models`.
- Blocker: không có.
- Bước tiếp theo: push nhánh, mở PR vào `dev`; thử với khoá thật của từng hãng.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-11-24T22:33:18+07:00` — claude-agent: tạo task; không hỗ trợ Azure/Voyage/Jina/mô hình cục bộ; danh sách là gợi
  ý, không thay ô gõ tay.
- `2026-11-24T22:33:18+07:00` — claude-agent: mọi AC đạt, review approved; chuyển `done`.
- `2026-11-24T22:44:10+07:00` — claude-agent: người dùng yêu cầu xoá mô tả thừa trong hộp thoại, chọn làm tiếp trên nhánh
  này (gộp chung PR); thêm AC-05, S-03; mở lại rồi đóng sau verification/review.

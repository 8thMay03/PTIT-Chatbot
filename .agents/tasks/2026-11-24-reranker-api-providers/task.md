# Task: Thêm nhà cung cấp reranker phổ biến (Cohere, Jina, Voyage, Pinecone, HF TEI)

- ID: `2026-11-24-reranker-api-providers`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("thêm các provider phổ biến cho reranker")
- Tạo lúc: `2026-11-24T18:49:57+07:00`
- Cập nhật lúc: `2026-11-24T19:00:30+07:00`

## Yêu cầu và kết quả mong muốn

Hộp thoại "Thêm mô hình" của "Xếp hạng lại (Rerank)" chỉ có `cross-encoder` (cục bộ) và `rerank_api` (một endpoint
chuẩn Cohere, admin tự nhập Base URL). Voyage, Pinecone và HF TEI không dùng được vì khác định dạng; Cohere/Jina phải
tự gõ Base URL. Cần thêm nhà cung cấp riêng như phần embedding (task `2026-11-24-embedding-api-providers`).

**Hiện trạng** (nhánh `dev` tại `8d9b134`):

- `app/retrieval/reranker.py` `call_rerank_api` chỉ gửi `POST {base_url}/rerank` dạng Cohere (`documents`, `top_n`,
  `Authorization: Bearer`) và đọc `results[].relevance_score`.
- `app/core/model_profiles.py` reranker chỉ có `cross-encoder`, `rerank_api`.
- Confidence gate, `get_runtime_config_dict`, frontend `rerankScoreApplies` coi chỉ `cross-encoder`/`rerank_api` là
  điểm tuyệt đối.

Định dạng API đã đối chiếu tài liệu chính thức (2026-11-24):

| Provider | Endpoint | Xác thực | Body | Response |
|---|---|---|---|---|
| Cohere | `https://api.cohere.com/v2/rerank` | `Authorization: Bearer` | `model, query, documents[str], top_n` | `results[].index/relevance_score` |
| Jina | `https://api.jina.ai/v1/rerank` | `Authorization: Bearer` | `model, query, documents[str], top_n, return_documents` | `results[].index/relevance_score` |
| Voyage | `https://api.voyageai.com/v1/rerank` | `Authorization: Bearer` | `model, query, documents[str], top_k` | `data[].index/relevance_score` |
| Pinecone | `https://api.pinecone.io/rerank` | `Api-Key` + `X-Pinecone-Api-Version` | `model, query, documents[{text}], top_n, return_documents` | `data[].index/score` |
| HF TEI | `{base_url}/rerank` (tự host) | `Authorization: Bearer` (tuỳ chọn) | `query, texts[str]` | mảng `[{index, score}]` |

Mixedbread không thêm: API rerank độc lập không còn trong tài liệu hiện hành.

## Phạm vi

- Bao gồm: client rerank theo provider, model profiles, endpoint kiểm tra kết nối, confidence gate/config, UI hộp
  thoại thêm mô hình (danh sách provider, trường, gợi ý, khoá, logo), tài liệu `.env.example`, test.
- Ngoài phạm vi: đổi ngưỡng hiệu chỉnh của confidence gate; chia lô tài liệu (số ứng viên mặc định nhỏ hơn giới hạn
  từng dịch vụ); SDK của từng hãng.
- Ràng buộc: giữ `rerank_api` cho profile/`.env` cũ; khoá chỉ gửi tới đúng nhà cung cấp; URL cố định của hãng không
  phụ thuộc allowlist, Base URL do admin nhập (TEI, `rerank_api`) vẫn qua allowlist.

## Tiêu chí nghiệm thu

- [x] AC-01: Tạo được profile reranker `cohere`, `jina`, `voyage`, `pinecone` (bắt buộc khoá, không Base URL) và `tei`
  (bắt buộc Base URL qua allowlist và tên mô hình để hiển thị, khoá tuỳ chọn); khoá không trả về client; đổi provider không mang khoá cũ.
- [x] AC-02: Request/response của từng provider đúng bảng trên; response sai định dạng/HTTP lỗi → `RerankAPIError`, câu
  hỏi quay về heuristic.
- [x] AC-03: "Kiểm tra kết nối" chạy được cho mọi provider API; khoá profile chỉ dùng khi cùng provider.
- [x] AC-04: Confidence gate và `calibrated_min_rerank_score` coi mọi provider API như `rerank_api`.
- [x] AC-05: UI hiện các provider mới với trường, gợi ý mô hình, quy tắc khoá, nút kiểm tra kết nối; test frontend qua.
- [x] AC-06: Toàn bộ test backend và frontend liên quan qua.

## Tài liệu và phụ thuộc

- `.agents/tasks/2026-11-21-api-reranker/`, `.agents/tasks/2026-11-24-embedding-api-providers/`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01, S-02 xong; verification `passed`, review `approved` (self_review, R-01 deferred). Mã ở commit
  `c62d938` nhánh `feat/reranker-api-providers`, mở PR vào `dev`.
- Blocker: không có.
- Bước tiếp theo: merge PR; thử "Kiểm tra kết nối" với khoá thật của từng hãng.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-11-24T18:49:57+07:00` — claude-agent: tạo task, chọn Cohere/Jina/Voyage/Pinecone/TEI; bỏ Mixedbread.
- `2026-11-24T19:00:30+07:00` — claude-agent: mọi AC đạt, review approved; chuyển `done`.

# Task: Reranker qua API (Base URL + API key)

- ID: `2026-11-21-api-reranker`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("phần cấu hình mô hình reranking không cho phép nhập base url và api key sao" → "tạo task
  mới cho tính năng cấu hình model rerank đi")
- Tạo lúc: `2026-11-21T21:33:21+07:00`
- Cập nhật lúc: `2026-11-21T22:04:53+07:00`

## Yêu cầu và kết quả mong muốn

Admin muốn cấu hình mô hình xếp hạng lại (reranker) gọi qua API, có Base URL và API key, giống LLM.

**Hiện trạng** (nhánh `dev` tại `430f2ca`):

- Backend chỉ có hai cách xếp hạng lại: `heuristic` và `cross-encoder`.
  - `cross-encoder` chạy cục bộ: `app/retrieval/reranker.py` gọi `sentence_transformers.CrossEncoder(settings.reranker_model)`.
  - Lỗi bất kỳ khi nạp/chấm điểm thì âm thầm quay về heuristic, không log, không báo ra giao diện.
- `app/core/model_profiles.py`:
  - `_PROVIDER_FIELDS` chỉ có `("reranker", "cross-encoder"): {"model": True}`. Trường khác bị bỏ khi lưu.
  - `_KEYED` không gồm reranker nên từ chối lưu API key.
  - `_apply_reranker` chỉ chép `provider`, `model`.
- Frontend (`models/catalog.js`): `RERANKER_PROVIDERS` chỉ có Cross-Encoder, `FIELDS.reranker` chỉ có ô mô hình,
  `KEY_RULES.reranker = {}`. Hộp thoại thêm/sửa sinh trường theo catalog nên tự hiện ô mới khi catalog có.
- Confidence gate (`app/generation/confidence.py`) chỉ dùng tín hiệu rerank khi `reranker_provider == "cross-encoder"`.
  Ngưỡng lấy từ `RERANK_THRESHOLDS` theo tên mô hình; hiện chỉ có một mô hình được hiệu chỉnh (thang logit, -1.65).
- Dữ liệu cũ, chưa dùng: `config.py` (`providers.reranker`) và `api/schemas.py` liệt kê `"cohere"` cho reranker, nhưng
  không có code chạy.

**Kết quả cần có** (theo quyết định D-01 … D-06 bên dưới):

- Nhà cung cấp reranker mới `rerank_api` (tên hiển thị "Rerank API"), gọi chuẩn `/rerank` của Cohere.
- Profile loại này có tên hiển thị, Base URL (bắt buộc, qua allowlist), mô hình (bắt buộc) và API key (tuỳ chọn, mã hoá,
  không bao giờ trả về client).
- Chọn "Dùng" có hiệu lực ngay như reranker hiện tại.
- Lỗi thì quay về heuristic và ghi log cảnh báo. Cross-Encoder cũng ghi log khi lỗi.
- Có nút "Kiểm tra kết nối"; hộp thoại ghi rõ nội dung tài liệu được gửi tới dịch vụ.

## Quyết định

Người dùng đồng ý đề xuất của claude-agent lúc `2026-11-21T21:49:01+07:00`.

- D-01 — Dịch vụ: một provider `rerank_api` theo chuẩn `/rerank` của Cohere.
  - Dùng được cho Cohere, Jina, vLLM, Infinity.
  - Request: `POST {base_url}/rerank`, body `{model, query, documents: [text…], top_n}`, header
    `Authorization: Bearer <key>` khi có khoá.
  - Response: `results: [{index, relevance_score}]`.
  - Base URL do admin nhập đầy đủ tới trước `/rerank` (ví dụ `https://api.cohere.com/v2`, `https://api.jina.ai/v1`,
    `http://localhost:8000/v1`).
  - Voyage (`data` thay `results`) và HF TEI (`{query, texts}`) ngoài phạm vi; thêm bộ chuyển đổi khi cần.
- D-02 — API key tuỳ chọn; không dự phòng bằng khoá `.env`.
  - Máy chủ tự host thường không cần khoá. Dịch vụ cần khoá trả 401 và "Kiểm tra kết nối" báo lỗi.
  - Không gửi khoá của máy chủ tới Base URL do admin nhập, cùng lý do với LLM `openai_compatible`.
- D-03 — Confidence gate với `rerank_api`:
  - Có ghi đè `RETRIEVAL_MIN_RERANK_SCORE` thì dùng (`rerank_source = "override"`).
  - Không có thì `rerank_source = "uncalibrated"` và bỏ tín hiệu rerank; BM25/vector vẫn kiểm tra.
  - Không dùng `RERANK_THRESHOLDS` của cross-encoder cho provider này, kể cả khi trùng tên mô hình (thang điểm khác).
  - Hiệu chỉnh bằng `scripts.eval_confidence` cho mô hình API: task riêng.
- D-04 — Khi API lỗi, quay về heuristic cho câu hỏi đó.
  - Lỗi gồm timeout, lỗi mạng, HTTP ≥ 400, response sai định dạng, `index` ngoài phạm vi.
  - Timeout 8 giây.
  - Ghi log cảnh báo gồm provider, mô hình, host, loại lỗi/mã HTTP. Không ghi khoá, nội dung câu hỏi hay nội dung đoạn.
- D-05 — Cross-Encoder hiện tại cũng ghi log cảnh báo khi lỗi, theo cùng quy tắc D-04. Hành vi quay về heuristic giữ
  nguyên.
- D-06 — Hộp thoại reranker API:
  - Ghi chú "Nội dung các đoạn tài liệu được gửi tới dịch vụ này."
  - Xoá `"cohere"` khỏi `providers.reranker` (`config.py`, `api/schemas.py`); thay bằng `rerank_api`.

## Phạm vi

- Bao gồm:
  - Backend:
    - `app/core/model_profiles.py`, `app/core/config.py` (trường `reranker_base_url`, `reranker_api_key`,
      `providers.reranker`), `app/core/config_store.py` (trường bí mật, `RERANKER_PROFILE_FIELDS`).
    - `app/retrieval/reranker.py` (client HTTP, log lỗi cho cả cross-encoder).
    - `app/api/schemas.py`, router model-profiles (endpoint kiểm tra kết nối reranker).
    - `app/generation/confidence.py` (D-03).
    - Test: `tests/test_reranker.py`, `tests/test_model_profiles.py`, `tests/test_config_api.py`,
      `tests/test_retrieval_confidence.py` và test mới nếu cần.
  - Frontend:
    - `frontend/src/models/catalog.js` (provider, trường, `KEY_RULES`), `frontend/src/models/ModelKindPanel.jsx`
      (kiểm tra kết nối cho reranker, ghi chú gửi dữ liệu).
    - `frontend/src/api/modelProfiles.js`, `frontend/src/settings/pipelineSummary.js` (nhãn provider).
    - Test tương ứng.
- Ngoài phạm vi:
  - Voyage, HF TEI, SDK riêng của từng hãng.
  - Hiệu chỉnh ngưỡng cho mô hình API.
  - `HF_TOKEN` cho cross-encoder private.
  - Thay đổi heuristic; hiện lỗi reranker ra giao diện.
- Ràng buộc:
  - Không làm hỏng `heuristic`/`cross-encoder` hiện có.
  - API key chỉ lưu dạng mã hoá (`config_crypto`), không ghi vào log, không trả về client.
  - Base URL phải qua `validate_llm_url`/allowlist (chống SSRF); áp lại khi chọn profile vì allowlist có thể đã thu hẹp.
  - Timeout 8 giây (D-04).

## Tiêu chí nghiệm thu

- [x] AC-01: Tạo/sửa profile reranker `rerank_api` với Base URL, mô hình, API key tuỳ chọn.
  - Thiếu Base URL hoặc mô hình, hay URL ngoài allowlist, thì bị từ chối (422).
  - Khoá được mã hoá, `has_api_key` đúng, response không chứa khoá.
  - Đổi sang `cross-encoder` thì xoá khoá đã lưu.
- [x] AC-02: "Dùng" profile `rerank_api` áp ngay `reranker_provider/model/base_url/api_key` và còn sau khởi động lại.
  - Về Heuristic hoặc chọn cross-encoder thì xoá `base_url`/`api_key`.
  - Sửa profile đang dùng thì áp lại.
  - Không dùng khoá `.env` khi profile không có khoá (D-02).
- [x] AC-03: `Reranker.rerank` với `rerank_api`:
  - Gửi request đúng D-01 (có/không header `Authorization` theo khoá).
  - Sắp theo `relevance_score`, ghi `rerank_score`/`score`, giữ `rrf_score`, trả tối đa `top_k`.
- [x] AC-04: Timeout, lỗi mạng, HTTP ≥ 400, response sai định dạng hoặc `index` ngoài phạm vi thì kết quả bằng heuristic.
  - Có một log cảnh báo không chứa khoá, câu hỏi hay nội dung đoạn (D-04).
  - Cross-Encoder lỗi cũng log theo cùng quy tắc (D-05).
- [x] AC-05: Confidence gate với `rerank_api`: có ghi đè thì dùng ngưỡng ghi đè; không có thì `uncalibrated`, bỏ tín
  hiệu rerank; không dùng `RERANK_THRESHOLDS` (D-03). Có test cho cả hai trường hợp.
- [x] AC-06: Endpoint kiểm tra kết nối reranker.
  - Gửi một truy vấn mẫu với hai đoạn, trả `{success, message, latency_ms}`, không lưu gì.
  - Dùng khoá đã lưu của `profile_id` khi ô khoá để trống; URL ngoài allowlist bị từ chối.
- [x] AC-07: Giao diện:
  - Hộp thoại thêm/sửa reranker có lựa chọn Cross-Encoder / Rerank API.
  - Rerank API hiện Base URL, mô hình, API key (tuỳ chọn), ghi chú gửi dữ liệu và nút "Kiểm tra kết nối".
  - Thẻ khâu, danh sách, dải bước hiện đúng tên nhà cung cấp.
  - `providers.reranker` không còn `"cohere"` (D-06).
- [x] AC-08: `pytest` backend (Postgres qua Docker), `npm test` và `npm run build` frontend đạt; có ảnh chụp hộp thoại
  reranker API sáng/tối.

## Tài liệu và phụ thuộc

- Task trước: `.agents/tasks/2026-10-30-model-registry/` (kho mô hình), `2026-11-21-models-settings-redesign/` (giao
  diện hiện tại, PR #78 đã merge vào `dev`), `2026-11-08-rag18-confidence-gate/` (ngưỡng rerank).
- Code: `backend/app/retrieval/reranker.py`, `backend/app/core/model_profiles.py`, `backend/app/core/config.py`
  (`validate_llm_url`, `llm_url_allowlist`), `backend/app/generation/confidence.py`, `frontend/src/models/catalog.js`.
- Chuẩn `/rerank`: tài liệu Cohere Rerank API (`results[].index`, `results[].relevance_score`).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai S-01 … S-03, kiểm chứng AC-01 … AC-08 (`verification.md` `passed`), self review `approved`.
  Thay đổi nằm trong working tree nhánh `feat/api-reranker` (tách từ `dev` tại `430f2ca`), chưa commit.
- Blocker: không có.
- Bước tiếp theo: commit/PR vào `dev` khi người dùng yêu cầu. Trước khi dùng, admin thêm origin dịch vụ rerank vào
  `LLM_BASE_URL_ALLOWLIST`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-21T21:33:21+07:00 — claude-agent: tạo task `draft` theo yêu cầu người dùng; ghi hiện trạng, đề xuất và câu hỏi
  mở Q1–Q4.
- 2026-11-21T21:49:01+07:00 — claude-agent: người dùng đồng ý đề xuất cho Q1–Q4 và hai đề xuất thêm. Ghi D-01 … D-06,
  chốt phạm vi và AC (thêm AC-04 về log lỗi, tách AC giao diện thành AC-07); chuyển `ready`.
- 2026-11-21T22:04:53+07:00 — claude-agent: triển khai theo yêu cầu người dùng. Mở rộng phạm vi file nhỏ (ghi ở
  `implementation.md` S-03): `fields.jsx` (icon), `ConfigView.jsx` và `RetrievalTestPanel.jsx` (ô ngưỡng rerank cho
  Rerank API, cần cho ghi đè D-03), `.env.example` (ghi chú biến mới). Kiểm chứng đạt, review `approved`; chuyển `done`.

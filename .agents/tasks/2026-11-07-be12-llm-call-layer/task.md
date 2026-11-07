# Task: BE-12 · Lớp gọi LLM: bỏ retry lồng nhau, deadline tổng, tái dùng client, không lộ lỗi nội bộ

- ID: `2026-11-07-be12-llm-call-layer`
- Trạng thái: `in_review`
- Coordinator: `claude-be12`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-07T18:45:20+07:00`
- Cập nhật lúc: `2026-11-07T21:53:18+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: Notion "PTIT Chatbot" › BE-12 (P1, rà soát toàn hệ thống ngày 2026-11-05) — https://app.notion.com/p/40f334d296eb816db37ae369082ac42a

Hành vi hiện tại (đối chiếu trên `dev` @ `50a2f65`, đã gồm BE-10, BE-11, BE-13; số dòng Notion đã lệch, dưới đây là vị trí mới):

- **Retry lồng nhau.** `OpenAIProvider._get_client` (`backend/app/llm/providers/openai_provider.py:31-44`), `OpenAICompatibleProvider` (`openai_compatible_provider.py:39-50`) và `AzureOpenAIProvider` (`azure_openai_provider.py:49-53`) tạo client SDK không đặt `max_retries` → SDK tự retry 2 lần. Bên ngoài, `BaseLLMProvider._execute_with_retry` (`backend/app/llm/base.py:131-161`) retry thêm `LLM_MAX_RETRIES=2` lần với `time.sleep` 1s, 2s. Một lời gọi `generate` có thể tới **9** request × `LLM_TIMEOUT=30s` + backoff.
- **Không có deadline theo lượt chat.** Một lượt chat gọi LLM tới 3 lần nối tiếp: viết lại câu hỏi (`query_rewriter.py`, khi `QUERY_REWRITE_USE_LLM`), sinh đa truy vấn (`multi_query.py`), sinh câu trả lời. Hai bước đầu nuốt lỗi rồi dùng dự phòng, nên khi LLM sập, mỗi bước vẫn chờ hết retry trước khi sang bước sau.
- **Retry sai loại lỗi ở Gemini.** `GeminiProvider` gói `HTTPError` thành `LLMProviderError("Gemini API error 400: …")` bên trong hàm retry (`gemini_provider.py:126-128`) → `_is_retryable_error` không thấy status code nên retry cả 400/401/403. Key Gemini nằm trong query string URL (`?key=…`, dòng 107 và 144).
- **Không tái dùng client.** `get_llm_provider()` (`backend/app/llm/factory.py:95-104`) tạo provider mới (và client HTTP mới) ở **mỗi** lần gọi — tới 3 lần mỗi lượt chat. Gemini dùng `urllib` nên không có keep-alive.
- **Lộ lỗi nội bộ cho trình duyệt.** `/api/chat/stream` gửi `{"type":"error","message": f"Retrieval failed: {exc}"}` (`backend/app/api/routes.py:1379-1388`) và `str(LLMStreamError)` gồm cả thông điệp exception của provider (`routes.py:1418-1422`, `generation/llm.py:86`). `ChatView.jsx:321-329` hiện nguyên `message`. Cùng chuỗi đó được lưu vào `metadata.error.message` của tin nhắn (`routes.py:1319, 1385, 1445, 1507`).
- **Thông điệp dự phòng gây hiểu nhầm.** `_extractive_answer` (`backend/app/generation/llm.py:97-106`) luôn nói "Chưa cấu hình API Key cho LLM…", kể cả khi đã có key nhưng LLM lỗi tạm thời.

Kết quả cần có:

- Một tầng retry duy nhất: SDK `max_retries=0`; `_execute_with_retry` thử tối đa `1 + LLM_MAX_RETRIES` lần (mặc định 3), chỉ với lỗi tạm thời; Gemini giữ status code để không retry lỗi 4xx.
- Deadline tổng cho phần LLM của mỗi lượt chat; mọi lần thử và backoff bị cắt theo thời gian còn lại; hết deadline thì dừng và dùng dự phòng/báo lỗi trước deadline.
- Provider được cache theo "dấu vân tay" cấu hình LLM; hai lượt chat liên tiếp dùng cùng client; admin đổi model/key (qua `/config` hoặc chọn profile LLM) thì lần gọi sau tạo client mới. Gemini dùng client HTTP giữ kết nối và gửi key qua header.
- Client chỉ nhận thông điệp chung tiếng Việt kèm mã tham chiếu (request id); chi tiết exception chỉ nằm trong log (kèm cùng mã).
- Hai thông điệp dự phòng riêng: chưa cấu hình LLM, và LLM tạm lỗi.

## Phạm vi

- Bao gồm: `backend/app/llm/` (base, factory, 4 provider), `backend/app/generation/{llm,query_rewriter,multi_query,rag_chain}.py` (truyền deadline, thông điệp dự phòng), `backend/app/api/routes.py` (chỉ khối chat: event `error`, `metadata.error`, request id, lỗi `/api/chat`), `backend/app/core/config.py` + `.env.example` (setting deadline), test.
- Ngoài phạm vi:
  - Route admin "thử kết nối LLM" (`routes.py:444-476`) vẫn trả chi tiết lỗi cho admin (admin cần chẩn đoán) — chỉ hưởng lợi từ việc bỏ retry SDK.
  - Lớp embedding (BE-13 đã làm), reranker.
  - Middleware request id cho toàn bộ API (chỉ làm cho lượt chat).
  - Giao diện lỗi chat (FE-15): `ChatView.jsx` đã hiện `message` từ backend nên không cần sửa.
  - Circuit breaker giữa các request / giới hạn đồng thời LLM toàn process.
- Ràng buộc:
  - Giữ hợp đồng NDJSON (`start`/`step`/`reasoning`/`delta`/`done`/`error`; `error` là event kết thúc), BE-11 (3 pha session, lưu khi client ngắt), BE-10 (thứ tự 422/400/503/429), BE-13 (503 embedding).
  - `LLM_MAX_RETRIES` giữ tên và mặc định; ý nghĩa đổi thành "số lần thử lại của tầng duy nhất" — ghi rõ trong `.env.example`.
  - Không gọi mạng trong test; đếm request bằng transport giả của `httpx`.
  - Không ghi key vào log/metadata (lưu ý OpenAI có thể trả thông điệp chứa một phần key).

## Tiêu chí nghiệm thu

- [x] AC-01: Provider OpenAI (và OpenAI-compatible, Azure) nhận 5xx liên tục: tổng số HTTP request ≤ `1 + LLM_MAX_RETRIES` (= 3 với mặc định) cho một lần `generate`; lỗi 400/401/403/404 không retry (1 request). Gemini cũng vậy với status code thật. — V-01 `passed`.
- [x] AC-02: Lượt chat (cả `/api/chat` và `/api/chat/stream`) khi LLM treo/lỗi liên tục kết thúc trong `LLM_TURN_DEADLINE_SECONDS` + sai số nhỏ (test đồng hồ/timeout giả), không còn bước nào chờ quá thời gian còn lại; câu trả lời dự phòng hoặc event `error` được gửi trước deadline. — V-02 `passed`.
- [x] AC-03: Hai lượt chat liên tiếp (gồm cả các bước rewrite/multi-query) dùng **cùng một** instance provider và client HTTP; đổi `openai_model`/key qua `PUT /api/config` hoặc chọn profile LLM khác → lần gọi sau dùng provider mới; cache an toàn khi nhiều thread. — V-03 `passed`.
- [x] AC-04: Event `error` của stream (lỗi retrieval, lỗi LLM giữa chừng, lỗi nội bộ) và `detail` lỗi của `/api/chat` không chứa text exception gốc; có mã tham chiếu trùng với dòng log chứa chi tiết. `metadata.error` lưu DB chỉ gồm loại lỗi, mã tham chiếu, tên lớp exception. — V-04 `passed`.
- [x] AC-05: Dự phòng extractive phân biệt hai trường hợp: LLM chưa cấu hình → thông điệp "chưa cấu hình"; LLM lỗi/hết deadline → thông điệp "tạm thời gặp sự cố". Không còn chuỗi "Chưa cấu hình API Key cho LLM" khi đã có key. — V-05 `passed`.
- [x] AC-06: Toàn bộ test backend pass; test chat/stream của BE-10/BE-11/BE-13 không đổi hành vi ngoài những điểm nêu trên. — V-06 `passed` (954 passed, 1 skipped).

## Tài liệu và phụ thuộc

- Notion BE-12: https://app.notion.com/p/40f334d296eb816db37ae369082ac42a
- Nền: `dev` @ `50a2f65`. Liên quan: BE-11 (`2026-11-06-be11-stream-db-session` — khối chat 3 pha), BE-10 (`2026-11-07-be10-chat-rate-limit`), BE-13 (`2026-11-07-be13-safe-embedding-startup` — cùng kiểu cache theo dấu vân tay), `2026-10-30-model-registry` (chọn profile LLM chép trường vào `settings`), `2026-10-28-persist-runtime-config`, FE-14 (nginx `proxy_read_timeout` 300s cho stream — deadline LLM phải nhỏ hơn), FE-15.
- Code: `backend/app/llm/base.py`, `backend/app/llm/factory.py`, `backend/app/llm/providers/*.py`, `backend/app/generation/llm.py`, `query_rewriter.py`, `multi_query.py`, `rag_chain.py`, `backend/app/api/routes.py` (khối chat), `backend/app/core/config.py`, `.env.example`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Câu hỏi mở cho người yêu cầu

- Q-01: Deadline? Đề xuất `LLM_TURN_DEADLINE_SECONDS=60` áp cho rewrite + multi-query + sinh câu trả lời **tới token đầu tiên** (stream) hoặc toàn bộ (`/api/chat`). Khi stream đã chạy, mỗi lần đọc chunk vẫn bị giới hạn bởi `LLM_TIMEOUT`, không cắt câu trả lời dài đang sinh bình thường. 60s nhỏ hơn timeout stream 300s của nginx (FE-14).
- Q-02: Khi một lời gọi LLM trong lượt đã thất bại hết retry (LLM đang sập), các bước **tùy chọn** sau đó (multi-query) có bỏ qua LLM ngay không? Đề xuất **có** — dùng dự phòng rule-based, dành thời gian còn lại cho bước sinh câu trả lời.
- Q-03: `/api/chat` (không stream) khi lỗi không lường trước: hiện ném tiếp → 500 "Internal Server Error". Đề xuất trả **503** `{"detail": "Hệ thống đang bận, vui lòng thử lại sau. (Mã: <id>)"}` + header `X-Request-ID`. Lỗi LLM thông thường vẫn ra câu trả lời dự phòng 200 như hiện tại.
- Q-04: Mã tham chiếu: đề xuất 12 ký tự hex ngẫu nhiên mỗi lượt chat, đưa vào `message` của event `error` (để frontend hiện được mà không phải sửa), thêm trường `request_id` riêng trong event và header `X-Request-ID` của cả hai route chat.

### Trả lời câu hỏi mở

- 2026-11-07T21:53:18+07:00 — người yêu cầu giao "implement task be12" mà không đổi đề xuất; `claude-be12` áp dụng nguyên các đề xuất Q-01..Q-04 (deadline 60s, bỏ qua bước tùy chọn khi LLM đã sập, `/api/chat` lỗi bất ngờ → 503, mã 12 hex trong `message` + `request_id` + `X-Request-ID`). Người yêu cầu có thể đổi khi review PR.

## Trạng thái hiện tại

- Tóm tắt: S-01..S-05 xong trên nhánh `feat/llm-call-layer`, commit và mở PR vào `dev` theo yêu cầu người yêu cầu. V-01..V-06 `passed`; V-07 chỉ chạy bản rút gọn (thời gian thật, không qua trình duyệt) — xem `verification.md`. Review vòng 2 `independent` (`grok-review-be12`) `approved`; R-01..R-04 đều `low`, `deferred`.
- Blocker: không.
- Bước tiếp theo: người yêu cầu review/merge PR; chạy V-07 trên dev server trước khi merge nếu muốn; tạo task riêng cho R-01 (Gemini `includeThoughts`). Coordinator chuyển task sang `done` sau khi merge.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-07T18:45:20+07:00 — claude-be12: tạo task `draft` từ Notion BE-12, dựa trên `dev` @ `50a2f65`. Thêm vào phạm vi lỗi retry 4xx của Gemini và key trong URL (phát hiện khi đối chiếu code). Route thử kết nối của admin, middleware request id toàn API và UI lỗi (FE-15) để ngoài phạm vi.
- 2026-11-07T21:53:18+07:00 — claude-be12: `draft` → `in_progress` → `in_review`. Nền thực tế `dev` @ `7d1a717` (đã gồm FE-14, PR #53; không chạm file của task này). Thêm vào phạm vi: lỗi nội bộ bất ngờ của stream kết thúc bằng event `error` chung thay vì cắt kết nối (AC-04 "lỗi nội bộ"); fixture chặn request mạng thật qua `httpx` trong test. Phát hiện ngoài phạm vi: Gemini từ chối `includeThoughts` trong `generationConfig` (R-01, đề nghị task riêng).

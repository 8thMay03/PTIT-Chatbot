# Đánh giá kỹ thuật & Kế hoạch cải thiện — PTIT RAG Chatbot

> **Phiên bản:** 1.0 · **Ngày:** 13/09/2026 · **Nhánh khảo sát:** `fix/ui-ux` (commit `310cad3`)
> **Phạm vi:** toàn bộ `backend/` (~8.400 LOC Python, 149 test) và `frontend/` (~9.000 LOC JSX + CSS)

---

## 1. Tóm tắt điều hành

Dự án đã có **kiến trúc RAG đúng chuẩn và khá đầy đủ** cho một MVP: hybrid retrieval (pgvector + BM25 + RRF), parent-child chunking, multi-query, reranker, guardrail phạm vi, confidence gate, citation chuẩn hoá, streaming NDJSON, Alembic migration, Docker Compose. Phần chunker xử lý bảng Markdown/HTML là điểm sáng rõ rệt — đây là thứ quyết định chất lượng với tài liệu quy chế đầy bảng biểu.

Tuy nhiên, khoảng cách lớn nhất hiện nay **không phải là thuật toán RAG mà là độ tin cậy của hệ thống**:

| Trục | Trạng thái | Nhận xét ngắn |
| --- | --- | --- |
| Chất lượng RAG (retrieval/generation) | 🟢 Tốt | Kiến trúc đúng, cần tinh chỉnh & đo lường tự động |
| Tính đúng đắn khi vận hành | 🔴 Có lỗi chặn | 1 lỗi 500 bật được từ chính UI, 1 lỗi ingest sai chiều vector |
| Bảo mật | 🔴 Chưa có | Không auth trên bất kỳ endpoint nào; API key ghi được qua HTTP; nguy cơ SSRF |
| Dữ liệu nguồn | 🟠 Hạn chế | Chỉ đọc `.md`/`.txt`; PDF 37MB trong `data/` **không được dùng**; có file trùng lặp |
| Frontend — kiến trúc | 🟠 Nợ kỹ thuật | 4 file "god component" 440–1330 dòng, 1 file CSS 4.803 dòng, không router, không test |
| Frontend — tính trung thực UI | 🔴 Gây mất tin cậy | Nhiều chức năng là *giả*: log cứng, toggle không lưu, toast báo "thành công" khi lỗi, nút dark mode không hoạt động |
| Quan sát & vận hành | 🔴 Chưa có | Không log có cấu trúc, không request-id, không metric, không CI |

**Ba việc cần làm trước tiên (tuần này):** (1) sửa lỗi `NameError` khi tắt guardrail, (2) thêm auth + khoá đường ghi API key qua `/api/config`, (3) xoá hoặc hiện thực hoá các UI giả.

---

## 2. Bảng phát hiện theo mức ưu tiên

### 2.1 P0 — Lỗi chặn / rủi ro bảo mật (sửa ngay)

| # | Phát hiện | Vị trí | Hệ quả |
| --- | --- | --- | --- |
| P0-1 | `scope` chỉ được gán khi `guardrail_scope_enabled=True`, nhưng luôn được đọc ở cuối hàm → `NameError` | `backend/app/generation/rag_chain.py:114` và `:183` | Tắt guardrail từ màn **Cấu hình** (UI có sẵn toggle này) ⇒ **mọi** request `/api/chat` và `/api/chat/stream` trả 500 |
| P0-2 | Không có xác thực/phân quyền trên bất kỳ endpoint nào | `backend/app/api/routes.py` (toàn bộ) | Ai truy cập được port 8000 đều có thể xoá tài liệu, ghi đè cấu hình, đọc toàn bộ chunk |
| P0-3 | `PUT /api/config` cho phép ghi `api_key` và `base_url` của LLM | `routes.py:68`, `core/config.py` → `update_runtime_config` | Kẻ tấn công trỏ `base_url` sang server của họ ⇒ **toàn bộ câu hỏi + ngữ cảnh tài liệu bị exfiltrate**; key hợp lệ bị thay bằng key của họ |
| P0-4 | `POST /api/config/test-llm` gọi HTTP tới `base_url`/`endpoint` do client cung cấp | `routes.py:81` | SSRF: dùng backend làm proxy quét mạng nội bộ / metadata service |
| P0-5 | Cột vector cố định `Vector(1536)` nhưng fallback embedding là `HashEmbeddingModel` 384 chiều, và fallback này *im lặng* | `db/models.py:57`, `embeddings/models.py:13`, `embeddings/embedder.py` | Chọn `sentence-transformers` (không có trong Docker image — nằm ở extra `ml`) hoặc provider lạ ⇒ ingest hỏng do lệch chiều, hoặc index rác mà không ai biết |
| P0-6 | `DELETE /api/documents/{id}` và `POST /api/ingest` không xác thực, `/ingest` xoá sạch bảng `documents` | `routes.py:136,241`, `db/repositories.py` → `replace_knowledge_base` | Mất toàn bộ knowledge base bằng một lệnh `curl` |

### 2.2 P1 — Sai lệch hành vi / chất lượng (backend)

| # | Phát hiện | Vị trí | Hệ quả |
| --- | --- | --- | --- |
| P1-1 | Đổi `embedding.provider/model` qua API **không có tác dụng**: `Retriever` và `IngestionPipeline` là singleton tạo lúc import | `retrieval/retriever.py:35`, `ingestion/pipeline.py:269` | Màn **Mô hình** cho chọn embedding nhưng backend vẫn dùng model cũ tới khi restart ⇒ người dùng bị lừa |
| P1-2 | Đổi embedding **không re-embed** chunk cũ | `ingestion/pipeline.py` | Trộn hai không gian vector khác nhau ⇒ cosine vô nghĩa, retrieval tụt mạnh, không báo lỗi |
| P1-3 | `generate_stream` hard-code `temperature=0.2`, bỏ qua `settings.llm_temperature` | `generation/llm.py:61` | Câu trả lời streaming (đường đi chính của UI) khác câu trả lời non-stream và khác cấu hình ⇒ số đo Ragas không phản ánh trải nghiệm thật |
| P1-4 | Chỉ hỗ trợ `.md`/`.txt`; `data/` đang chứa `Sổ tay sinh viên D26.pdf` (37MB) và `so-tay-sinh-vien-d21.pdf` — **không bao giờ được ingest** | `ingestion/loaders.py` → `SUPPORTED_EXTENSIONS` | Nguồn chính thức của trường là PDF/DOCX; hiện phải convert tay ngoài hệ thống |
| P1-5 | `data/` có 2 file `.md` trùng nội dung (`... (1) (1).md` và `... _1_ _1_.md`, cùng 978.432 bytes) | `data/` | Mỗi câu hỏi trả về 2 chunk gần như giống nhau trong top-k ⇒ **lãng phí ~50% context window**, citation nhiễu |
| P1-6 | Guardrail phạm vi là **allow-list từ khoá** cứng | `guardrails/patterns.py` → `DOMAIN_TERMS` | False-negative cao: "Ai là trưởng phòng CTSV?", "Phòng một cửa mở cửa mấy giờ?" bị từ chối oan. Đây là nguồn khiếu nại số 1 của loại chatbot này |
| P1-7 | Ingest + embedding chạy **đồng bộ trong request** | `routes.py:217`, `pipeline.py` | Upload file lớn ⇒ request treo hàng chục giây/timeout; không tiến độ, không retry |
| P1-8 | BM25 index nạp **toàn bộ chunk vào RAM** mỗi process, rebuild toàn bộ khi invalidate | `retrieval/bm25.py` → `_load_chunks` | Không scale (mỗi uvicorn worker một bản copy); nên dùng `tsvector` + GIN của Postgres |
| P1-9 | Commit DB **bên trong generator streaming** với session lấy từ `Depends` | `routes.py` → `chat_stream` | Client ngắt giữa stream ⇒ teardown session chồng lấn, nguy cơ mất lượt hội thoại / leak connection |
| P1-10 | `init_db()` gọi `create_all` lúc khởi động **song song với** Alembic | `main.py:11`, `pipeline.py:33,76,118` | Hai nguồn sự thật về schema; DB production có thể lệch migration mà không ai biết |
| P1-11 | Không có API danh sách hội thoại / lịch sử | `routes.py` | DB đã lưu `Conversation`/`Message` nhưng UI không đọc lại được ⇒ F5 là mất hết; sidebar không có history |
| P1-12 | `GET /api/documents/{id}` đọc **toàn bộ** file vào RAM qua `read_text()` | `routes.py` → `get_document` | File ~1MB × nhiều request đồng thời ⇒ áp lực bộ nhớ vô ích (UI chỉ cần preview + chunk) |
| P1-13 | Ingest lại **re-embed toàn bộ** dù `content_hash` không đổi | `pipeline.py` → `ingest_documents` | Chi phí embedding lặp lại mỗi lần bấm "Reindex" |

### 2.3 P1 — Frontend

| # | Phát hiện | Vị trí | Hệ quả |
| --- | --- | --- | --- |
| F1-1 | **Nút dark/light mode không hoạt động**: `theme` chỉ đổi icon; `styles.css` không có một token dark nào (0 lần khớp `dark`/`prefers-color-scheme`) | `App.jsx:48,174`, `styles.css` | Chức năng quảng cáo nhưng vô hiệu |
| F1-2 | **Bảng log là dữ liệu cứng** (`log-1..3`, timestamp `10/08/2026`) | `DatasetView.jsx:79-102` | Người dùng / hội đồng tưởng là log thật |
| F1-3 | **Toggle bật/tắt tài liệu & chunk chỉ là state local**, không gửi lên server | `DatasetView.jsx:206`, `DocumentView.jsx` | Tắt tài liệu nhưng nó vẫn được retrieve ⇒ hiểu sai nghiêm trọng |
| F1-4 | **Toast báo thành công khi lưu thất bại**: `catch` → `showToast("Đã lưu cấu hình cục bộ.", "success")` | `ConfigView.jsx:140`, `ModelsView.jsx:487` | Che lỗi backend; người dùng tin là đã lưu |
| F1-5 | Panel "Retrieval test" gửi 6 tham số backend **bỏ qua hoàn toàn** (`similarity_threshold`, `vector_similarity_weight`, `rerank_model`, `use_knowledge_graph`, `cross_language_search`, `meta_data`) | `DatasetView.jsx:375`, `api/schemas.py` → `RetrievalTestRequest` | Tinh chỉnh trên UI không tác động gì tới kết quả |
| F1-6 | `ConfigView` lỗi tải cấu hình ⇒ chỉ `console.warn`, giữ giá trị mặc định | `ConfigView.jsx:82` | Hiển thị cấu hình sai, người dùng sửa trên nền sai |
| F1-7 | `DocumentView` tải **toàn bộ** chunk (batch 500, lặp đến hết) rồi phân trang client-side | `DocumentView.jsx:65` | Tài liệu ~1MB ⇒ hàng nghìn chunk trong RAM, TTI chậm |
| F1-8 | `dangerouslySetInnerHTML` với markdown tự viết tay | `ChatView.jsx` → `renderMarkdown` / `inline` | Hiện có escape nên tạm an toàn, nhưng mỗi lần sửa regex là một lần rủi ro XSS; và **không render được bảng** — trong khi nội dung nguồn đầy bảng |
| F1-9 | Bấm "Dừng" chỉ `abort()` phía client | `ChatView.jsx` → `stopStreaming` | Backend vẫn sinh hết, vẫn tốn token, vẫn commit vào DB |
| F1-10 | `top_k: 4` hard-code trong request chat | `ChatView.jsx:213` | Sửa `top_k` ở màn Cấu hình không ảnh hưởng chat |
| F1-11 | `lang-selector` là `<div>` không có hành vi; không có i18n | `App.jsx:159` | UI hứa đa ngôn ngữ nhưng không có |

### 2.4 P2 — Nợ kỹ thuật & chất lượng dài hạn

- **Frontend không có tầng data**: 17 lời gọi `fetch` rải rác 6 file, mỗi nơi tự xử lý loading/error/abort; `api.js` chỉ có 1 dòng export base URL.
- **God components**: `DatasetView.jsx` 1.330 dòng (~25 `useState`), `ModelsView.jsx` 1.004, `ConfigView.jsx` 589, `ChatView.jsx` 478. `styles.css` 4.803 dòng không chia module, không design token.
- **`SettingsView.jsx` là dead code** (7 dòng, không ai import).
- Không có ESLint/Prettier, không TypeScript, **không một test frontend nào**, không error boundary, không `React.lazy`.
- **Không có CI** (`.github/` không tồn tại) dù đã có 149 test backend — chúng chỉ chạy khi có người nhớ chạy.
- Không có log có cấu trúc / request-id; không metric (latency p95, TTFT, tỉ lệ từ chối, chi phí token).
- Không rate limit ⇒ một script có thể đốt hết quota LLM.
- README mô tả script `scripts/migrate_sqlite_to_postgres.py` **không tồn tại** (`backend/scripts/` chỉ có `evaluate`, `evaluate_ragas`, `ingest`).
- `Vector(1536)` hard-code trong cả model và migration khiến biến `VECTOR_DIM` trong config là lời hứa suông.
- `PgVectorStore.add/delete` bị vô hiệu bằng thủ thuật `hasattr(..., "session_factory")` trong pipeline — abstraction rò rỉ, khó đọc, khó test.
- Cấu hình runtime chỉ sống trong RAM của **một** process: mất khi restart, không đồng bộ giữa nhiều worker.

---

## 3. Nhận xét chi tiết — Backend

### 3.1 Điểm mạnh nên giữ

- **Chunker** (`ingestion/chunker.py`, 657 dòng): tách section theo heading Markdown, giữ nguyên bảng Markdown/HTML thành block độc lập, cắt bảng quá khổ có prefix ngữ cảnh. Đúng hướng cho tài liệu quy chế.
- **Parent-child retrieval** (`retrieval/parent_child.py`): gom child theo parent, giữ `evidence_text` và `matched_child_count`. Pattern tốt để vừa chính xác khi match vừa đủ ngữ cảnh khi sinh.
- **Citation pipeline**: `_normalize_answer_citations` loại bỏ số citation bịa và buộc câu trả lời có nguồn hợp lệ — chống hallucination ở tầng hậu xử lý, rất đáng giá.
- **Guardrail nhiều lớp**: chuẩn hoá Unicode/leetspeak, phát hiện prompt injection ở **cả** câu hỏi lẫn **nội dung chunk truy xuất** (indirect injection) — hiếm thấy ở dự án cùng cấp.
- **Confidence gate** tách riêng, ngưỡng cấu hình được, có test.
- **149 test** cùng fixture Ragas 100 câu — nền tảng tốt để tự động hoá đánh giá.

### 3.2 Vấn đề kiến trúc cần xử lý

**(a) Cấu hình runtime là biến toàn cục có thể ghi.**
`update_runtime_config` gán trực tiếp vào singleton `settings`. Hệ quả: không thread-safe, không bền vững, không chia sẻ giữa worker, và trộn lẫn hai loại cấu hình khác nhau về bản chất — *bí mật hạ tầng* (API key, `DATABASE_URL`) và *tham số nghiệp vụ* (top_k, ngưỡng, bật/tắt reranker).
→ Đề xuất: secret **chỉ** từ biến môi trường, không bao giờ ghi qua API. Tham số nghiệp vụ lưu bảng `app_settings` trong Postgres, đọc qua `ConfigService` có cache TTL ngắn.

**(b) Singleton khởi tạo lúc import.**
`retriever`, `rag_chain`, `ingestion_pipeline` tạo ở module scope ⇒ import là mở kết nối và tải model; test phải lách; cấu hình runtime không vào được. → Chuyển sang FastAPI dependency + `lru_cache` có key theo `(provider, model)`, và dùng `lifespan` để khởi tạo/giải phóng.

**(c) BM25 in-process.**
Nên chuyển sang full-text search của Postgres: cột `tsvector` + index GIN, xếp hạng bằng `ts_rank_cd`. Ưu điểm: không giữ RAM, không rebuild, nhất quán giữa các worker, filter được theo `document_id`. Với tiếng Việt dùng cấu hình `simple` kèm chuẩn hoá dấu; giữ `rank_bm25` làm chế độ dự phòng.

**(d) Không có filter metadata khi search.**
`PgVectorStore.search` không nhận `document_id`/`status` ⇒ không thể (i) bật/tắt tài liệu như UI hứa, (ii) giới hạn theo khoá/ngành, (iii) tách phiên bản sổ tay D21 vs D26 — trong khi PRD nói rõ nỗi đau là "dùng sai phiên bản tài liệu".

**(e) Không có nền tác vụ nền.**
Ingest, embedding, re-embed, đánh giá Ragas đều là việc dài. Cần job runner (đơn giản nhất: bảng `jobs` + `BackgroundTasks`; đúng đắn hơn: ARQ/Celery + Redis) và endpoint `GET /api/jobs/{id}` để UI hiển thị tiến độ.

### 3.3 Chất lượng RAG — hướng tinh chỉnh

1. **Chống trùng lặp ở tầng retrieval**: dedupe theo hash nội dung chunk và theo độ tương đồng ≥ 0.95 trước khi đưa vào prompt (xử lý P1-5 tận gốc, không chỉ xoá file).
2. **Guardrail hai tầng**: bỏ hard-reject bằng allow-list; thay bằng *soft gate* — luôn retrieve, có `strong_context` thì trả lời, không thì từ chối. Giữ allow-list chỉ cho các loại yêu cầu rõ ràng ngoài phạm vi (viết code, sáng tác). Cách này giảm false-negative mà không tăng hallucination, vì confidence gate đã gánh phần đó.
3. **Cross-encoder reranker tiếng Việt**: hiện mặc định là `heuristic`; `mmarco-mMiniLMv2-L12-H384-v1` đã khai báo nhưng `sentence-transformers` không có trong image Docker ⇒ luôn im lặng rơi về heuristic. Cần đo A/B rõ ràng và đưa vào image nếu thắng.
4. **Trích xuất "Điều / Khoản / Điểm"** thành metadata có cấu trúc lúc chunk ⇒ trả lời được dạng "theo Điều 12 Khoản 3" và filter chính xác hơn.
5. **Đo lường tự động**: `scripts/evaluate_ragas.py` đã có; đưa vào CI (nightly) trên bộ 100 câu, lưu kết quả theo commit để thấy hồi quy. Lưu ý: phải đo qua **đúng đường đi streaming** (sau khi sửa P1-3) mới có ý nghĩa.

---

## 4. Nhận xét chi tiết — Frontend

### 4.1 Điểm mạnh

- Xử lý NDJSON streaming đúng cách: đọc `ReadableStream`, buffer theo dòng, `AbortController`.
- Citation chip tương tác: click số `[n]` → scroll tới source card tương ứng. Trải nghiệm tốt, đúng tinh thần "kiểm chứng được".
- Dùng `hidden` để giữ `ChatView` mounted khi đổi view ⇒ không mất hội thoại khi sang màn khác.
- Tiếng Việt nhất quán, tone thân thiện, gợi ý câu hỏi mẫu hợp bối cảnh.
- Đồng bộ view với URL hash + localStorage (dù là router tự viết).

### 4.2 Vấn đề then chốt

**(a) Vấn đề lớn nhất là *tính trung thực của UI*.** Một chatbot tra cứu quy chế bán được bằng niềm tin. Hiện có ít nhất 6 chỗ UI nói một điều mà hệ thống làm điều khác (F1-1…F1-6). Với hội đồng hoặc người dùng thật, phát hiện một chỗ giả sẽ làm mất tin vào toàn bộ phần còn lại — kể cả những phần thực sự tốt.
**Nguyên tắc đề xuất: mỗi control trên UI phải hoặc thay đổi hành vi hệ thống, hoặc bị xoá.** Nếu muốn giữ để demo lộ trình, đánh dấu rõ "Sắp có" và đặt `disabled`.

**(b) Không có tầng data.** Đề xuất `src/api/client.js` (một hàm `request()` gom base URL, JSON, timeout, abort, chuẩn hoá lỗi từ `detail` của FastAPI) + module theo domain + TanStack Query cho cache/invalidate/retry. Riêng việc này xoá được vài trăm dòng lặp và toàn bộ lớp lỗi "quên set loading/error".

**(c) Cấu trúc file.** Tách theo feature:

```
src/
  api/            client.js, documents.js, config.js, chat.js
  features/
    chat/         ChatView.jsx, MessageList.jsx, Composer.jsx, SourceList.jsx, useChatStream.js
    dataset/      DatasetView.jsx, DocumentTable.jsx, UploadDropzone.jsx, RetrievalTestPanel.jsx
    document/     DocumentView.jsx, ChunkList.jsx, ChunkCard.jsx
    config/       ConfigView.jsx, sections/*
    models/       ModelsView.jsx, ProviderCard.jsx
  components/     ui nguyên thủy (Button, Toggle, Toast, Modal, Table)
  styles/         tokens.css, base.css + CSS Module cạnh mỗi component
```

Mục tiêu cụ thể: **không file JSX nào vượt 250 dòng**; `styles.css` 4.803 dòng → tokens + module.

**(d) Dark mode làm cho đúng.** Định nghĩa toàn bộ màu thành CSS custom property trên `:root`, ghi đè trong `@media (prefers-color-scheme: dark)` và `:root[data-theme="dark"]`; `App` set `document.documentElement.dataset.theme` và lưu localStorage.

**(e) Markdown và bảng.** Thay renderer tự viết bằng `react-markdown` + `remark-gfm` (bảng!) + `rehype-sanitize`, giữ một plugin nhỏ để biến `[n]` thành citation chip. Nguồn dữ liệu là sổ tay đầy bảng — hiện bảng trong câu trả lời hiển thị thành văn bản dính liền.

**(f) Lịch sử hội thoại.** Backend đã lưu đủ. Cần `GET /api/conversations`, `GET /api/conversations/{id}/messages` và đưa danh sách vào sidebar (nơi hiện chỉ có "Mẹo sử dụng"). Đây là tính năng người dùng mong đợi nhất mà chi phí thấp nhất.

**(g) Khả năng truy cập & trạng thái.** Thiếu: skeleton thay vì trắng trang, empty state có hành động, thông báo lỗi nêu được cách xử lý, focus trap trong modal, `aria-live` cho vùng câu trả lời đang stream, điều hướng bàn phím cho bảng tài liệu, tương phản đạt WCAG AA.

---

## 5. Kế hoạch cải thiện

Bốn giai đoạn, xếp theo *rủi ro giảm được trên mỗi giờ bỏ ra*.

### Giai đoạn 0 — Chặn chảy máu (2–3 ngày)

| # | Việc | File | Tiêu chí hoàn thành |
| --- | --- | --- | --- |
| 0.1 | Sửa `NameError` guardrail: khởi tạo `scope_reason = "guardrail_disabled"` và dùng biến đó trong `retrieval_debug` | `rag_chain.py:183` | Test mới: `guardrail_scope_enabled=False` ⇒ `/api/chat` trả 200 |
| 0.2 | **Bỏ hoàn toàn** đường ghi API key / base_url qua `PUT /api/config`; chuyển sang biến môi trường | `api/schemas.py`, `core/config.py` | Payload chứa `api_key` bị từ chối 400; có test khẳng định |
| 0.3 | Thêm auth: token admin (header `X-Admin-Token`) cho mọi endpoint ghi, `/config*` và `/retrieval/test`; `/chat*` để public hoặc sau token sinh viên | `api/deps.py` (mới), `routes.py` | Test: gọi không token ⇒ 401 trên toàn bộ route quản trị |
| 0.4 | `test-llm`: chỉ cho phép `base_url` thuộc allow-list (domain provider đã biết + host nội bộ cấu hình sẵn) | `llm/factory.py`, `routes.py:81` | Test: URL lạ / `169.254.169.254` ⇒ 400 |
| 0.5 | Fail-fast embedding: bỏ fallback im lặng sang `HashEmbeddingModel`; validate chiều vector khớp `VECTOR_DIM` trước khi ghi | `embeddings/embedder.py`, `pipeline.py` | Test: provider sai ⇒ lỗi có thông điệp rõ, không ghi DB |
| 0.6 | Dọn UI giả: xoá bảng log cứng, xoá hoặc `disabled` toggle bật-tắt tài liệu & chunk, xoá 6 field retrieval-test không dùng, sửa toast lỗi thành `type="error"` | `DatasetView.jsx`, `DocumentView.jsx`, `ConfigView.jsx`, `ModelsView.jsx` | Rà soát: mỗi control còn lại đều gọi API hoặc đổi state có thật |
| 0.7 | Dark mode thật, hoặc bỏ nút | `App.jsx`, `styles.css` | Toggle đổi cả bảng màu và giữ được qua reload |
| 0.8 | Xoá file `.md` trùng trong `data/`, xoá `SettingsView.jsx`, sửa README (script không tồn tại) | `data/`, `frontend/src/`, `README.md` | `git grep` không còn tham chiếu chết |
| 0.9 | Rate limit cơ bản cho `/api/chat*` theo IP | middleware mới | Vượt ngưỡng ⇒ 429 |

### Giai đoạn 1 — Đúng đắn & nền tảng (1–1,5 tuần)

| # | Việc | Chi tiết | Tiêu chí hoàn thành |
| --- | --- | --- | --- |
| 1.1 | Bỏ singleton import-time | `get_retriever()`, `get_rag_chain()`, `get_pipeline()` qua `Depends` + `lru_cache` theo key cấu hình; khởi tạo trong `lifespan` | Đổi embedding qua API ⇒ lần retrieve sau dùng model mới (có test) |
| 1.2 | Cấu hình nghiệp vụ vào DB | Bảng `app_settings` (key, value JSON, updated_at) + `ConfigService` cache 5s; secret vẫn từ env | Restart backend ⇒ cấu hình đã lưu còn nguyên |
| 1.3 | Một nguồn sự thật về schema | Bỏ `create_all` khỏi `main.py`/`pipeline.py`; entrypoint chạy `alembic upgrade head`; `VECTOR_DIM` lái `Vector(dim)` qua migration | `alembic check` sạch; startup fail nếu chưa migrate |
| 1.4 | Streaming nhất quán | Dùng `settings.llm_temperature`; tách phần persist khỏi generator (session riêng, `try/finally`), ghi lại cả khi client ngắt | Test: ngắt giữa stream ⇒ lượt hội thoại vẫn lưu, không leak connection |
| 1.5 | Hủy thật khi bấm "Dừng" | Truyền cancel token / `request.is_disconnected()` xuống provider, đóng stream LLM | Log xác nhận đã dừng gọi upstream |
| 1.6 | API lịch sử hội thoại | `GET /api/conversations?limit`, `GET /api/conversations/{id}/messages`, `DELETE /api/conversations/{id}` (kèm sources) | Sidebar liệt kê và mở lại được hội thoại cũ |
| 1.7 | Ingest tăng tiến | So `content_hash`: không đổi ⇒ bỏ qua, không re-embed; `/ingest` không xoá trắng mà upsert + xoá bản mồ côi | Bấm "Reindex" lần 2 ⇒ 0 lời gọi embedding (test đếm) |
| 1.8 | Tác vụ nền + tiến độ | Bảng `jobs`, `POST /api/documents` trả `202 {job_id}`, `GET /api/jobs/{id}` | UI hiện % và trạng thái; upload không timeout |
| 1.9 | Log có cấu trúc + request-id | JSON log, middleware gắn `X-Request-ID`, log mỗi truy vấn: latency, top_k, số chunk, `strong_context`, guardrail reason, provider/model | Tra được một câu hỏi cụ thể từ log trong dưới 1 phút |
| 1.10 | CI GitHub Actions | job `backend`: ruff + pytest (Postgres service); job `frontend`: eslint + build + vitest | PR không xanh thì không merge |
| 1.11 | Tầng data frontend | `api/client.js` + module theo domain + TanStack Query; xoá 17 `fetch` rải rác | Không còn `fetch(` ngoài `src/api/` |
| 1.12 | Truyền `top_k` từ cấu hình vào chat | Bỏ hard-code `4` | Đổi top_k ở màn Cấu hình ⇒ request chat phản ánh đúng |

### Giai đoạn 2 — Chất lượng RAG & trải nghiệm (2–3 tuần)

| # | Việc | Chi tiết | Tiêu chí / mục tiêu đo |
| --- | --- | --- | --- |
| 2.1 | **Loader PDF/DOCX** | `pypdf`/`pdfplumber` (+ tuỳ chọn OCR cho trang scan), `python-docx`; giữ heading và bảng; lưu `page_number` vào metadata | Ingest được `Sổ tay sinh viên D26.pdf` trực tiếp; citation hiện số trang |
| 2.2 | Dedupe chunk | Bỏ trùng theo hash + ngưỡng tương đồng trước khi vào prompt | Không còn 2 chunk giống nhau trong top-k (test hồi quy) |
| 2.3 | Full-text search Postgres | `tsvector` + GIN thay BM25 in-memory, hỗ trợ filter `document_id`/`status` | Bỏ được toàn bộ chunk khỏi RAM; p95 retrieval không xấu hơn |
| 2.4 | Guardrail soft-gate | Bỏ hard-reject theo allow-list; giữ chặn loại yêu cầu ngoài phạm vi; quyết định cuối dựa confidence gate | Trên bộ 100 câu: **false-reject < 2%**, faithfulness không giảm |
| 2.5 | Bật/tắt & phiên bản tài liệu thật | Cột `is_active`, `version`, `academic_year`; filter trong retrieval; UI điều khiển thật | Tắt sổ tay D21 ⇒ không còn citation từ D21 |
| 2.6 | Reranker cross-encoder | Đưa `sentence-transformers` vào image, đo A/B heuristic vs cross-encoder trên 100 câu | Chọn cấu hình thắng theo Context Precision; ghi lại số đo |
| 2.7 | Metadata Điều/Khoản/Điểm | Trích xuất có cấu trúc lúc chunk | Câu trả lời dẫn được "Điều 12 Khoản 3"; UI hiện đúng locator |
| 2.8 | Cache truy vấn | Cache embedding câu hỏi + cache câu trả lời cho câu hỏi trùng (TTL, invalidate khi reindex) | Câu hỏi lặp: TTFT < 300ms |
| 2.9 | Tái cấu trúc frontend theo feature | Tách god component, CSS token + module, error boundary, `React.lazy` cho màn quản trị | Không file JSX > 250 dòng; bundle màn chat giảm rõ rệt |
| 2.10 | Markdown đúng chuẩn | `react-markdown` + `remark-gfm` + `rehype-sanitize` + plugin citation | Bảng render thành `<table>`; bỏ `dangerouslySetInnerHTML` |
| 2.11 | Sidebar lịch sử + UX trạng thái | Danh sách hội thoại, đổi tên, xoá; skeleton; empty state; `aria-live` | Reload không mất hội thoại |
| 2.12 | Phản hồi người dùng | 👍/👎 kèm lý do trên mỗi câu trả lời, lưu cùng `retrieval_debug` | Có dữ liệu thật để cải thiện thay vì đoán |
| 2.13 | Test frontend | Vitest + RTL cho parse NDJSON, citation chip, luồng upload, form cấu hình; Playwright 1 luồng E2E | Coverage logic chat/dataset ≥ 60% |

### Giai đoạn 3 — Sẵn sàng vận hành (1–2 tuần, chạy song song được)

- **Bảo mật:** phân vai (sinh viên / admin), audit log cho mọi thay đổi tài liệu và cấu hình, secret qua vault/secret manager, CSP + security headers ở nginx, giới hạn kích thước và quét nội dung upload.
- **Quan sát:** Prometheus metrics (TTFT, latency p50/p95, tỉ lệ từ chối, chi phí token/ngày), health check phân tầng (DB / vector index / LLM), dashboard tối giản.
- **Vận hành:** backup tự động Postgres + kiểm thử restore định kỳ, hướng dẫn rollback migration, image production đa tầng (bỏ `--reload`, dùng `gunicorn -k uvicorn.workers.UvicornWorker`), tách compose dev/prod.
- **Tài liệu:** cập nhật README theo thực tế, ADR cho các quyết định chính (tại sao pgvector, tại sao parent-child, tại sao soft-gate), runbook xử lý sự cố.
- **Đánh giá liên tục:** chạy Ragas nightly trên 100 câu, lưu theo commit, cảnh báo khi tụt quá 3 điểm phần trăm.

---

## 6. Gợi ý sửa cụ thể cho các lỗi P0

**P0-1 — `rag_chain.py`**

```python
scope_allowed = True
scope_reason = "guardrail_disabled"
if settings.guardrail_scope_enabled:
    scope = check_scope(question, history)
    scope_allowed, scope_reason = scope.allowed, scope.reason
    if not scope_allowed:
        ...  # nhánh từ chối, giữ nguyên

# ... cuối hàm:
"guardrail": {"allowed": True, "reason": scope_reason},   # thay cho scope.reason
```

**P0-2 / P0-3 — `api/deps.py` (file mới)**

```python
from fastapi import Header, HTTPException
from app.core.config import settings

def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not settings.admin_api_token or x_admin_token != settings.admin_api_token:
        raise HTTPException(status_code=401, detail="Không có quyền truy cập.")
```

Gắn `dependencies=[Depends(require_admin)]` cho router quản trị (`/config*`, `/documents` ghi/xoá, `/ingest`, `/retrieval/test`), và **xoá** các field `*api_key*`, `base_url` khỏi `UpdateLLMConfig`.

**P0-5 — `embeddings/embedder.py`**

```python
def create_embedding_model() -> EmbeddingModel:
    provider = settings.embedding_provider.lower()
    if provider == "hash":                    # chỉ dùng trong test
        return HashEmbeddingModel(dimensions=settings.vector_dim)
    if provider == "openai":
        return OpenAIEmbeddingModel(settings.embedding_model, settings.openai_api_key)
    if provider == "sentence-transformers":
        return SentenceTransformerEmbeddingModel(settings.embedding_model)   # để lỗi nổi lên
    raise ValueError(f"EMBEDDING_PROVIDER không hỗ trợ: {provider!r}")
```

Kèm kiểm tra trước khi ghi: `len(embedding) == settings.vector_dim`, sai thì báo lỗi rõ ràng thay vì để Postgres báo lệch chiều.

---

## 7. Chỉ số theo dõi

| Chỉ số | Hiện tại (theo PRD) | Mục tiêu sau kế hoạch | Cách đo |
| --- | --- | --- | --- |
| Context Precision | 0.90 | ≥ 0.92 | `scripts/evaluate_ragas.py`, 100 câu, nightly |
| Context Recall | 0.95 | giữ ≥ 0.95 | như trên |
| Faithfulness | 0.93 | ≥ 0.95 | như trên |
| Answer Relevancy | 0.85 | ≥ 0.88 | như trên |
| **False-reject rate** (từ chối oan) | *chưa đo* | < 2% | bộ 50 câu trong phạm vi nhưng thiếu từ khoá domain |
| TTFT p95 | < 2s | < 1,5s (có cache: < 0,3s) | metric server |
| Số endpoint không auth | ~11 | 0 (trừ `/health`, `/chat*`) | test tự động |
| Control UI không có tác dụng | ≥ 8 | 0 | rà soát theo checklist |
| File JSX > 250 dòng | 4 | 0 | ESLint `max-lines` |
| Test frontend | 0 | ≥ 60% logic chính | Vitest coverage |
| CI trên mỗi PR | Không | Có | GitHub Actions |

---

## 8. Thứ tự thực thi khuyến nghị

1. **Tuần 1:** trọn Giai đoạn 0. Sau tuần này hệ thống không còn lỗi 500 bật được từ UI, không còn đường ghi API key qua HTTP, và UI không còn nói dối.
2. **Tuần 2–3:** Giai đoạn 1 theo thứ tự 1.1 → 1.4 → 1.6/1.7 → 1.9/1.10 → 1.11. Ưu tiên 1.6 (lịch sử hội thoại) vì đây là giá trị người dùng cảm nhận ngay với chi phí thấp nhất.
3. **Tuần 4–6:** Giai đoạn 2, bắt đầu bằng 2.1 (PDF/DOCX — mở khoá nguồn dữ liệu thật) và 2.4 (soft-gate — giảm từ chối oan). Mỗi thay đổi liên quan RAG **phải** kèm một lần chạy Ragas trước/sau.
4. **Song song từ tuần 3:** các phần vận hành của Giai đoạn 3.

> **Nguyên tắc xuyên suốt:** không thêm tính năng RAG mới trước khi các con số hiện tại được đo lại tự động trên mỗi commit. Nếu không, mọi tinh chỉnh đều là phỏng đoán.

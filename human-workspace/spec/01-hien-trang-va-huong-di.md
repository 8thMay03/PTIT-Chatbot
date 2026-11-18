# Spec — Hiện trạng hệ thống so với bài toán đồ án và hướng đi tiếp theo

- **Nguồn yêu cầu (chuẩn duy nhất):** `documents/Mô tả bài toán và phạm vi đồ án nhóm 5.docx.md`.
  Các file `documents/01-project-overview.md`, `02-prd.md`, `03-srs.md` được giữ lại để tham khảo nhưng **không dùng** nữa.
- **Baseline code:** commit `92aa804` (nhánh **`dev`**), cập nhật ngày 2026-11-09. Bản 2026-11-08 đánh giá trên `main @ 54a5582` — cũ hơn `dev` 140 commit, **không dùng nữa**.
- **Giả định:** dữ liệu tri thức 6 nhóm đã được Khánh chuẩn bị; đánh giá dưới đây chỉ xét theo chức năng nghiệp vụ.
- **Ký hiệu:** ✅ đáp ứng · 🟡 đáp ứng một phần · ❌ chưa có.
- **Phân công (chốt 2026-11-08, điều chỉnh so với Bảng 8):** Ngọc = toàn bộ frontend + toàn bộ backend không thuộc RAG (auth, API CN01–CN09, CSDL/migration, bộ nhớ đệm CN13, đo thời gian, triển khai), ứng dụng vỏ WebView, thiết kế, thực nghiệm phần thời gian. Khánh = **chỉ lõi RAG** (CN10, CN11, CN12, CN14, chỉ số chất lượng RAG) + khảo sát S-Link, dữ liệu.

---

## 1. Tóm tắt nhanh

| Hạng mục | Đánh giá |
|---|---|
| Lõi RAG (truy xuất lai, guardrail, citation, streaming) | 🟡 Đã mạnh hơn nhiều: chia đoạn theo Điều/Khoản/Điểm, `search_text`, bảng không mất dữ liệu, ngưỡng tin cậy đã hiệu chỉnh, phân biệt nguồn trích/nguồn liên quan, từ chối không kèm nguồn. **Còn thiếu:** câu không dấu (vẫn bị từ chối), tách từ tiếng Việt, cross-encoder mặc định, bộ nhớ đệm, metadata khóa/ngành, lọc hiệu lực |
| Quản lý tri thức | 🟡 Có nhiều dataset (bật/tắt), parse nền + tiến trình, tách bước parse/chia đoạn, sửa Markdown, xem file gốc, 3 parser (text/Docling/LlamaParse). **Chưa có** metadata nghiệp vụ (ngày ban hành, hết hạn, đối tượng), phiên bản |
| Người dùng & bảo mật | 🟡 Có tài khoản người dùng (email + mật khẩu, scrypt, cookie `ptit_user`), phiên ẩn danh `ptit_sid`, admin đăng nhập qua `ADMIN_EMAIL/ADMIN_PASSWORD` (cookie `ptit_admin`), mọi route quản trị có `require_admin`, rate limit chat, chống dò mật khẩu. **Chưa có:** mã SV, khóa/ngành, role trong bảng `users`, nhận danh tính từ ứng dụng vỏ |
| Phản hồi sinh viên (CN06, CN09) | ❌ Chưa có (admin mới xem được danh sách hội thoại) |
| Giao diện | 🟡 Đã tách `/` landing, `/login`, `/register`, `/chat`, `/admin` (lazy load), có lớp `api/` dùng chung, có Vitest. **Vẫn JS**, chưa TypeScript, chưa thiết kế mobile-first cho WebView, chưa có ứng dụng vỏ |
| Thực nghiệm | 🟡 Có `eval_retrieval.py` (hit@k, MRR, coverage@k; 4 chế độ bm25/vector/hybrid/full), `eval_confidence.py`, bộ 300 câu D26 + 56 câu không trả lời được, báo cáo ở `documents/rag-eval/`. **Chưa có** Precision@k theo span gán nhãn, p50/p95/TTFT, chế độ RAG cơ bản đầy đủ (chia cố định) |

---

## 2. Đánh giá theo chức năng (CN01–CN14)

### 2.1. Chức năng chung và sinh viên (Ngọc phụ trách)

| Mã | Chức năng | BE | FE | Bằng chứng trong code | Còn thiếu / hướng làm |
|---|---|:-:|:-:|---|---|
| CN01 | Đăng nhập (SV theo mã SV, admin; danh tính từ ứng dụng vỏ) | 🟡 | 🟡 | `POST /api/auth/register|login|logout`, `GET /api/auth/me` (`api/routes.py:295–375`); `core/user_auth.py` (scrypt, token HMAC); admin dùng chung `/login`, kiểm bằng `ADMIN_EMAIL` (`core/auth.py`); bảng `users` (`0005_users`): id, email, full_name, password_hash. FE: `auth/LoginPage.jsx`, `RegisterPage.jsx`, `components/UserMenu.jsx` | Đồ án yêu cầu **đăng nhập theo mã SV**, có khóa/ngành để phục vụ QT4 → thêm `student_code`, `cohort`, `major`, `role` vào `users` (hoặc bảng hồ sơ); quyết định có giữ đăng ký tự do không (SV thật do trường cấp); cầu nối nhận danh tính từ ứng dụng vỏ. Admin hiện chỉ có **1 tài khoản từ biến môi trường**, không lưu DB |
| CN02 | Hỏi đáp, hiển thị dần, hỏi nối tiếp | ✅ | ✅ | `POST /api/chat/stream` NDJSON với event `start`, `step`, `reasoning`, `delta`, `error`, `done` (`routes.py:1570`); lưu câu hỏi trước khi stream, lưu phần đã sinh khi client ngắt (`metadata.interrupted`); nút dừng, xử lý IME Enter; panel tiến trình suy luận (`components/ReasoningPanel.jsx`); retry + deadline LLM (`llm/budget.py`) | FE: tối ưu mobile/WebView; đo TTFT. Chất lượng câu không dấu/viết tắt thuộc CN11 (Khánh) |
| CN03 | Xem nguồn trích dẫn, bấm xem đoạn gốc | 🟡 | 🟡 | `public_citations` trả `citation_id`, tên văn bản, heading, section_path, Điều/Khoản/Điểm, `locator` (`generation/citations.py`); FE gắn nhãn "Nguồn trích dẫn"/"Nguồn liên quan" (`lib/citations.js`); câu từ chối không trả nguồn | Nguồn chưa có `chunk_id`, `document_id`, đoạn trích → API `GET /api/sources/{chunk_id}`; FE bottom-sheet xem đoạn gốc. Admin đã có `OriginalDocumentViewer` xem file gốc — có thể tái dùng một phần |
| CN04 | Gợi ý câu hỏi phổ biến + câu hỏi liên quan | ❌ | 🟡 | Danh sách `SUGGESTIONS` cố định trong `ChatView.jsx:24`; landing có `FaqList.jsx` tĩnh | BE: API câu hỏi phổ biến; câu hỏi liên quan sau mỗi câu trả lời (event `related`). FE: chip gợi ý |
| CN05 | Lịch sử hội thoại: xem, mở lại, đổi tên, xóa | ✅ | ✅ | `GET/PATCH/DELETE /api/conversations*` lọc theo owner của phiên (`user:<id>` hoặc `anon:<hash sid>`); admin xem mọi hội thoại qua `/api/admin/conversations*` | Khi chuyển sang đăng nhập bằng mã SV thì owner key theo SV; quyết định có cho chat ẩn danh không |
| CN06 | Đánh giá hữu ích/không hữu ích + góp ý | ❌ | ❌ | — | Bảng `feedback`; `PUT /api/messages/{id}/feedback`; stream phải trả `message_id`; nút 👍/👎 + ô góp ý |

### 2.2. Chức năng quản trị viên (Ngọc phụ trách API + giao diện; Khánh cung cấp lọc truy xuất theo hiệu lực)

| Mã | Chức năng | BE | FE | Bằng chứng trong code | Còn thiếu / hướng làm |
|---|---|:-:|:-:|---|---|
| CN07 | Quản lý tài liệu: tải lên kèm nhóm tri thức, nguồn, ngày ban hành, ngày hết hạn, đối tượng áp dụng; xem danh sách, các đoạn; xóa | 🟡 | 🟡 | Dataset CRUD + bật/tắt (`/api/datasets*`, `0008_datasets`, retrieval chỉ lấy dataset `enabled`); upload chạy nền `POST /api/documents` → `parse-jobs` có tiến trình (`ingestion/jobs.py`); chọn parser; tách parse / chia đoạn; sửa + tải Markdown; xem file gốc; chuyển tài liệu giữa dataset; xem các đoạn. FE: `datasets/*`, `DatasetView.jsx`, `DocumentView.jsx`, `MarkdownEditorView.jsx` | Dataset có thể đóng vai **nhóm tri thức**. Vẫn thiếu cột nguồn/cơ quan ban hành, ngày ban hành, ngày hết hạn, đối tượng áp dụng; cờ "bản scan" + trạng thái duyệt (đã có màn sửa Markdown — dùng làm bước duyệt) |
| CN08 | Cập nhật phiên bản tài liệu | ❌ | ❌ | Upload trùng tên trong cùng dataset **thay file** (`ingestion/uploads.py`), không lưu lịch sử | `version`, `supersedes_id`, `status` active/superseded/expired; API cập nhật phiên bản; hủy cache |
| CN09 | Xem phản hồi: câu bị đánh giá không hữu ích + câu không trả lời được | ❌ | ❌ | BE có API xem mọi hội thoại (`/api/admin/conversations*`, client `api/admin.js`) nhưng chưa có màn quản trị riêng cho phản hồi; `messages.metadata` có `retrieval_debug` (lý do confidence) nhưng chưa có `answer_status` | `answer_status` + API thống kê/lọc; màn quản trị lọc theo loại, thời gian |

### 2.3. Chức năng xử lý của hệ thống (Khánh: CN10, CN11, CN12, CN14 · Ngọc: CN13 bộ nhớ đệm)

| Mã | Chức năng | Hiện trạng | Bằng chứng trong code | Còn thiếu / hướng làm |
|---|---|:-:|---|---|
| CN10 | Trích xuất PDF, DOCX, PDF scan (OCR); giữ tiêu đề, bảng; admin kiểm tra bản scan | 🟡 | Parser `text`, `docling`, `llamaparse` (chọn tier) (`parsers/`); chuẩn hóa heading dùng chung (`parsers/normalize.py`); bảng giữ nguyên, ghép bảng ngắt trang; lưu `documents.parsed_text`, admin sửa Markdown rồi mới chia đoạn; `DOCLING_OCR_ENABLED` mặc định **tắt**, bật toàn cục | OCR theo từng file (hoặc chọn LlamaParse cho bản scan); trạng thái "chờ duyệt" trước khi chia đoạn — luồng tách bước đã có, chỉ thiếu trạng thái |
| CN11 | Chuẩn hóa câu không dấu, mở rộng viết tắt; viết lại câu hỏi nối tiếp | 🟡 | `query_rewriter.py`: 7 từ viết tắt, follow-up rule-based; rewrite LLM **tắt** mặc định | **Lỗi nghiêm trọng vẫn còn:** `guardrails/` không đổi so với `main`; `check_scope` chạy trên **câu gốc** trước rewrite (`rag_chain.py:157`), `DOMAIN_TERMS` chỉ có dạng có dấu → "hoc phi bao nhieu" bị từ chối. Cần chuẩn hóa **trước** kiểm tra phạm vi, so khớp không dấu, từ điển viết tắt đầy đủ, rewrite follow-up có điều kiện |
| CN12 | Truy xuất lai BM25 + vector; xếp hạng lại bằng cross-encoder | 🟡 | pgvector + BM25 (trên `search_text`, có `bm25_norm_score`) + RRF + gộp đoạn cha; lọc theo dataset bật; reranker mặc định **heuristic** (`RERANKER_PROVIDER=heuristic`) | BM25 vẫn tách `\w+` (`retrieval/bm25.py:175`) → cần pyvi/underthesea; cross-encoder làm mặc định + đo thời gian; lọc `documents.status`/hết hạn (hiện **không** lọc) và theo khóa/ngành |
| CN13 | Bộ nhớ đệm câu trả lời có căn cứ, hết hạn theo tài liệu nguồn; không lưu câu từ chối | ❌ | Chỉ có cache provider LLM/embedding, không có cache câu trả lời | Bảng `answer_cache` + liên kết tài liệu; tra sau chuẩn hóa/viết lại; hủy khi tài liệu thay/hết hạn/xóa (QT6) |
| CN14 | Từ chối câu ngoài phạm vi, chèn lệnh, không đủ căn cứ | 🟡 | Scope + injection (`guardrails/`); confidence gate đã hiệu chỉnh trên `bm25_norm`, vector, cross-encoder (`generation/confidence.py`, báo cáo `documents/rag-eval/rag-18/`); nhận diện câu từ chối của LLM để bỏ nguồn (`generation/refusal.py`) | (1) lỗi câu không dấu; (2) câu "không đủ căn cứ" chưa chỉ phòng ban (QT2); (3) chưa có `answer_status` lưu được để thống kê |

---

## 3. Đánh giá theo quy tắc nghiệp vụ (QT1–QT7)

| Mã | Quy tắc | Hiện trạng | Ghi chú |
|---|---|:-:|---|
| QT1 | Chỉ trả lời từ tài liệu, có ≥1 nguồn | 🟡 | Prompt bắt buộc citation; confidence gate; từ chối không kèm nguồn; FE phân biệt nguồn được trích. Nhưng câu trả lời **có nội dung mà không có `[n]` hợp lệ** vẫn được trả (chỉ đổi nhãn thành "Nguồn liên quan") → cần kiểm tra hậu sinh |
| QT2 | Không đủ căn cứ → thông báo rõ + chỉ phòng ban phụ trách | 🟡 | Chỉ trả `NO_CONTEXT_ANSWER` = "Chưa tìm thấy thông tin này trong tài liệu." (`generation/refusal.py`) |
| QT3 | Không dùng văn bản đã bị thay thế / thông báo hết hạn | ❌ | Chỉ lọc theo dataset bật/tắt; `documents.status` luôn `active`, không có ngày hết hạn |
| QT4 | Nêu rõ đối tượng áp dụng; chưa rõ khóa/ngành thì trả theo từng trường hợp | ❌ | Đoạn có Điều/Khoản/Điểm nhưng không có khóa/ngành; `users` không có khóa/ngành |
| QT5 | Thông tin quan trọng kèm khuyến cáo đối chiếu văn bản gốc | ❌ | Chưa có |
| QT6 | Hủy cache khi tài liệu nguồn bị thay/hết hạn | ❌ | Phụ thuộc CN13 |
| QT7 | Từ chối ngoài phạm vi và chèn lệnh | 🟡 | Có; vướng lỗi câu không dấu |

---

## 4. Nền tảng, công nghệ, phi chức năng

| Yêu cầu đồ án | Hiện trạng | Hướng làm |
|---|---|---|
| Khung chat web **ưu tiên điện thoại**, nhúng WebView | 🟡 Đã tách route `/chat` riêng khỏi `/admin` (admin lazy load, không lộ khi nhúng `/chat`); nhưng chat vẫn có sidebar kiểu desktop, có landing/đăng ký kiểu web công khai | Thiết kế lại `/chat` mobile-first; bỏ qua landing khi mở từ ứng dụng vỏ |
| Ứng dụng vỏ mô phỏng | ❌ | Expo + `react-native-webview` (D2) |
| Trang quản trị trên máy tính | ✅ `/admin` có đăng nhập, Dataset, Settings (Cấu hình RAG / Mô hình / Giao diện), chat thử kèm danh sách hội thoại | Thêm màn phản hồi (CN09), phiên bản (CN08) |
| TypeScript, React | 🟡 React 18 + **JavaScript**, có Vitest; chưa ESLint/TS | Chuyển TS (hoặc ghi rõ trong quyển) |
| FastAPI, PostgreSQL + pgvector | ✅ 8 migration (`0001`–`0008`) | — |
| LangChain | ❌ Lớp `app/llm/` tự viết (đã thêm retry, deadline theo lượt, cache provider) | Quyết định D1 |
| rank_bm25 + thư viện tách từ tiếng Việt | 🟡 rank_bm25, chưa tách từ | pyvi/underthesea (D5) |
| GPT-4o-mini / Gemini / LLM mã nguồn mở | ✅ Đa provider; **kho mô hình** LLM/embedding/reranker lưu DB, API key mã hóa (`core/model_profiles.py`, `0007`) | Chốt model thực nghiệm |
| Hiệu năng p50/p95, TTFT | 🟡 Mỗi `step` có `elapsed_ms`, lưu `steps` vào metadata; có `load_chat_stream.py` (kiểm tra tải, không đo p95/TTFT) | Lưu `latency_ms`, `ttft_ms`, `from_cache`; script benchmark |
| Bảo mật | 🟡 Route admin cần cookie admin; cấu hình lưu Postgres, key mã hóa (`core/config_store.py`, `config_crypto.py`); rate limit chat theo phiên + IP, giới hạn độ dài; chống dò mật khẩu; nginx production có security headers | Phân quyền SV theo mã SV; rate limit hiện **in-memory**, chỉ đúng khi 1 worker |

---

## 5. Thực nghiệm (Bảng 6, Bảng 7 của đồ án)

| Yêu cầu | Hiện trạng | Hướng làm |
|---|---|---|
| Cấu hình **RAG cơ bản** (chia cố định, chỉ vector) | 🟡 `eval_retrieval.py --mode vector` chỉ vector; nhưng chia đoạn luôn theo cấu trúc, và chat thật vẫn chạy BM25 + gate | `chunking_mode = fixed|structure`; `retrieval_mode` cho cả pipeline chat |
| Bật/tắt độc lập 6 cải tiến | 🟡 Có cờ multi-query, rewrite LLM, reranker, scope; thiếu cờ chuẩn hóa không dấu, cache | Mỗi cải tiến một cờ; script chạy ma trận |
| Recall@k, Precision@k, MRR theo **đoạn gán nhãn** | 🟡 hit@k, MRR, coverage@k theo `expected_terms` (không phụ thuộc chunk ID) trên 300 câu | Thêm Precision@k; cân nhắc nhãn span văn bản gốc |
| Faithfulness, Answer relevancy | ✅ Ragas (`scripts/evaluate_ragas.py`) | Chấm tay một mẫu |
| Tỷ lệ đúng, tỷ lệ từ chối đúng | 🟡 Bộ 56 câu không trả lời được + `eval_confidence.py` đo/quét ngưỡng gate | Tổng hợp thành chỉ số từ chối đúng end-to-end |
| p50, p95, TTFT có/không cache | ❌ | Script benchmark gọi API stream |
| Bộ 150–200 câu, chia tập điều chỉnh / tập kiểm tra | 🟡 `ptit_rag_300.json` (300 câu D26), `ptit_no_answer_56.json`, `table_questions.json`, `ptit_ragas_100.json`, `ptit_faq.json` | Bổ sung loại câu không dấu, viết tắt, nối tiếp, khóa/ngành; chia tập |

---

## 6. Lỗi và rủi ro còn tồn tại trên `dev`

1. **Câu không dấu bị từ chối** (`guardrails/patterns.py`, `scope.py`; scope chạy trước rewrite ở `rag_chain.py:157`). Chưa sửa.
2. **Không lọc hiệu lực:** truy xuất chỉ lọc dataset bật/tắt, không lọc `documents.status`/hết hạn (QT3).
3. **Upload trùng tên thay file** trong dataset, không lưu phiên bản (CN08).
4. **`init_db()` vẫn gọi `Base.metadata.create_all`** (`db/session.py:59`) song song Alembic — đã gây lỗi ở `0005_users` (commit `d115421`).
5. **Trạng thái trong bộ nhớ:** parse job, rate limit, chống dò mật khẩu chỉ đúng khi chạy 1 worker uvicorn.
6. **Đăng nhập không khớp đồ án:** email + đăng ký tự do, không có mã SV/khóa/ngành; admin chỉ 1 tài khoản từ env.
7. Câu trả lời không có trích dẫn hợp lệ vẫn được trả về (QT1).
8. README vẫn nhắc ChromaDB (`README.md:114`, `:421`).
9. Bản review giao diện ngày 2026-11-08 (mục 3b của `04-checklist-ngoc-fe-be.md`, ảnh `human-workspace/images/fe-review-2026-11-08/`) chụp trên `main` — **đã cũ**, FE `dev` đã làm lại gần như toàn bộ; cần review lại khi cần.

---

## 7. Hướng đi tiếp theo (thứ tự đề xuất)

1. **Thiết kế (Chương 2)** theo `02-ke-hoach-chuong-2-thiet-ke.md` — nhiều phần nay mô tả theo code có sẵn (auth, dataset, parse nền, cấu hình DB).
2. **Hợp đồng chung giữa Ngọc và Khánh** (cần chốt sớm):
   - Bổ sung cột metadata nghiệp vụ cho `documents` (nối với dataset = nhóm tri thức) và hồ sơ SV.
   - Event stream: thêm `message_id`, `answer_status`, `from_cache` vào `done`; event `related`.
   - Tách `RagChain` thành `prepare_query()` và `answer_stream()` — hiện `_retrieve_context` đã là generator theo bước (`step_event`), tách tương đối dễ.
   - Bộ lọc truy xuất: hiện đã nhận `dataset_ids`; mở rộng thêm `status`, hết hạn, đối tượng áp dụng.
3. **Song song:**
   - Khánh: sửa lỗi câu không dấu → tách từ tiếng Việt → cross-encoder mặc định → metadata khóa/ngành + lọc hiệu lực → chế độ RAG cơ bản + Precision@k. Chi tiết: `03-checklist-khanh-rag.md`.
   - Ngọc: hồ sơ SV (mã SV/khóa/ngành) → CN13 cache + đo thời gian → CN06/CN04/CN03 → CN07 metadata/CN08/CN09 → chat mobile-first + ứng dụng vỏ. Chi tiết: `04-checklist-ngoc-fe-be.md`.
4. **Thực nghiệm** sau khi đủ cờ bật/tắt; so sánh S-Link trên cùng tập kiểm tra.

## 8. Quyết định cần nhóm chốt

| # | Vấn đề | Hiện trạng trên `dev` | Đề xuất |
|---|---|---|---|
| D1 | Có dùng LangChain không | Lớp `app/llm/` tự viết, đã đầy đủ (retry, deadline, đa provider) | Sửa mô tả công nghệ trong quyển (thay LangChain bằng lớp provider tự viết) hoặc bọc LangChain ở lớp gọi LLM |
| D2 | Công nghệ ứng dụng vỏ | Chưa có | Expo (React Native) + react-native-webview |
| D3 | Nơi lưu bộ nhớ đệm | Chưa có | Bảng PostgreSQL |
| D4 | Cách đăng nhập sinh viên | **Đã code:** email + mật khẩu, đăng ký tự do, cookie HttpOnly (không dùng JWT) | Giữ cơ chế cookie; thêm mã SV/khóa/ngành; tài khoản SV do admin seed; ứng dụng vỏ truyền phiên. Cần chốt có tắt đăng ký tự do không |
| D5 | Thư viện tách từ | Chưa có | pyvi hoặc underthesea — Khánh chọn sau khi đo |
| D6 | Màn cấu hình RAG / mô hình | **Đã làm:** nằm trong `/admin` (Cấu hình, Mô hình), chỉ admin | Đã chốt theo code; ghi là màn "Thực nghiệm" trong quyển |
| D7 (mới) | Dataset có phải là "nhóm tri thức" không | Dataset tự đặt tên, bật/tắt | Dùng dataset làm nhóm tri thức (6 nhóm), gắn phòng ban (QT2) vào dataset |
| D8 (mới) | Giữ landing + chat ẩn danh không | Có landing `/`, chat ẩn danh qua `ptit_sid` | Đồ án yêu cầu SV đăng nhập; giữ ẩn danh chỉ để demo hoặc bỏ |

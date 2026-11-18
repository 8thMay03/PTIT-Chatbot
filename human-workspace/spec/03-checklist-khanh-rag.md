# Checklist — Khánh: lõi RAG (CN10, CN11, CN12, CN14, dữ liệu, khảo sát)

**Baseline:** `dev @ 92aa804`, cập nhật 2026-11-09 (bản 2026-11-08 dựa trên `main`, đã cũ).
**Phân công (chốt 2026-11-08):** Khánh **chỉ làm phần RAG** (+ khảo sát S-Link, dữ liệu theo Bảng 8). Toàn bộ backend không thuộc RAG (auth, API, CSDL/migration, bộ nhớ đệm CN13, đo thời gian, triển khai) do **Ngọc** làm — xem `04-checklist-ngoc-fe-be.md`.
Phạm vi code của Khánh: `backend/app/{guardrails,generation,retrieval,ingestion,parsers,embeddings,llm,vectordb}`, `backend/scripts/eval*.py`, `backend/tests/fixtures/`.
Ký hiệu: `[x]` đã có trên `dev` · `[ ]` còn phải làm. Mục 🔗 là **hợp đồng với Ngọc**.

**Cập nhật 2026-11-18 theo thiết kế Chương 2 đã Đạt (GVHD + hội đồng):** nguồn chuẩn là `documents/chuong-2/` (`import/2.6-csdl.sql`, `specs/2.5`–`2.7`, `chuan-bi-bao-ve.md`). Mục đánh dấu 🆕 là việc mới từ thiết kế; mục ghi ⚠️ là đã đổi so với bản 2026-11-09.

---

## 0. Hợp đồng dùng chung (chốt cùng Ngọc trước)
- [ ] 🔗 ⚠️ Lược đồ CSDL theo `documents/chuong-2/import/2.6-csdl.sql` (14 bảng): Ngọc viết model + migration. `chunks` cần: `chunk_strategy` (`fixed`/`legal`), `chunk_index`, `start_offset`, `end_offset` (vị trí trong `documents.extracted_text`), `section_path`, `tokenized_text`, `embedding`, `academic_year`, `expiry_date`; đối tượng áp dụng ở bảng `audiences` (cấp tài liệu hoặc cấp đoạn). Hiện có `search_text` (`0003`) và metadata JSON `legal_article`, `legal_clauses`, `legal_points`, parent/child.
- [ ] 🔗 Tách `RagChain` thành `prepare_query()` (chuẩn hóa → kiểm tra phạm vi/chèn lệnh → viết lại) và `answer_stream()` để Ngọc chèn cache. Hiện `_retrieve_context` trong `generation/rag_chain.py` đã là generator phát `step_event` theo từng bước — tách theo ranh giới bước `query_rewrite`.
- [ ] 🔗 ⚠️ Kết quả trả `answer_status` (`answered` / `out_of_scope` / `injection` / `no_context` / `error` — đúng CHECK trong SQL), `related_questions`, nguồn có `chunk_id` + `document_id` + đoạn trích + **tên văn bản, ngày ban hành**, Điều/Khoản. Hiện `public_citations` (`generation/citations.py`) chỉ trả tên văn bản, heading, section_path, Điều/Khoản/Điểm, `locator`, `citation_id`.
- [ ] 🔗 Truy xuất nhận bộ lọc `user_context` (khóa, ngành) cho QT4. Hiện `Retriever.retrieve` đã nhận `dataset_ids` → mở rộng cùng cơ chế.
- [ ] 🔗 🆕 Bộ truy xuất **đọc `knowledge_groups.cache_epoch` trước khi tìm kiếm** và trả các đoạn kèm nhóm tri thức + epoch đã đọc (2.5.2 msg 16–17, 22), để Ngọc chỉ ghi đệm khi epoch chưa đổi (QT6).
- [ ] 🔗 🆕 Sự kiện stream **thay câu trả lời đã hiển thị** khi sau sinh không có trích dẫn hợp lệ (QT1, 2.5.2 msg 35–41); câu trả lời chỉ được lưu **sau** bước kiểm. LLM lỗi giữa chừng: chỉ trả/lưu thông báo `error`.
- [ ] 🔗 🆕 Lịch sử hội thoại do API (Ngọc) đọc từ CSDL theo mã hội thoại, đã bỏ các lượt bị từ chối, rồi truyền vào `prepare_query()` (QA-18).
- [ ] 🔗 Cờ bật/tắt từng cải tiến trong `Settings` (`core/config.py`); lưu bảng `app_config_overrides` qua `core/config_store.py`, màn Cấu hình của admin đọc/ghi được (chốt 2026-11-18). Cờ: `NORMALIZATION_ENABLED`, `FOLLOW_UP_REWRITE_ENABLED`, `RETRIEVAL_MODE = vector | bm25 | hybrid`, `RERANKER_ENABLED`, `CHUNK_STRATEGY = fixed | legal` (+ `CACHE_ENABLED` của Ngọc).

## 1. Khảo sát và dữ liệu (công việc 1, 2, 4)
- [ ] Hoàn thiện khảo sát S-Link: đo thời gian phản hồi, đối chiếu văn bản gốc cho 48 câu; xuất bảng kết quả.
- [ ] Kho tài liệu 6 nhóm: mỗi file có metadata **nhóm tri thức, nguồn, ngày ban hành, ngày hết hạn, đối tượng áp dụng**. Đã có **dataset** (`0008_datasets`) — đề xuất mỗi nhóm tri thức là một dataset (quyết định D7).
- [ ] Bảng ánh xạ nhóm tri thức → phòng ban phụ trách + liên hệ (QT2) → dữ liệu khởi tạo `knowledge_groups` (`department`, `contact`, đúng một nhóm `is_default`).
- [ ] 🆕 Đánh dấu tài liệu chính thức / tổng hợp (`documents.is_official`) cho kho tài liệu (Bảng 3 "ưu tiên nguồn chính thức").
- [x] Bộ câu hỏi truy xuất lớn: `tests/fixtures/ptit_rag_300.json` (300 câu D26, `expected_terms`, có lint), `table_questions.json`.
- [x] Bộ câu không trả lời được: `ptit_no_answer_56.json` (56 câu, có lint).
- [ ] 🆕 Nhãn span: lưu (mã tài liệu, `start_offset`, `end_offset`, đoạn chữ) trên `extracted_text` của một **bản chụp kho** cố định; script báo lỗi khi chữ tại offset khác đoạn chữ đã lưu (Q-28).
- [ ] Bổ sung theo yêu cầu đồ án: đáp án chuẩn, nhãn "nên trả lời/nên từ chối" trên cùng một tập, loại câu (không dấu, viết tắt, nối tiếp, khóa/ngành, thuật ngữ, biên); chia tập điều chỉnh / tập kiểm tra. Bộ 300 câu hiện chỉ có tài liệu D26.
- [ ] Tập cặp câu có dấu/không dấu; tập câu hỏi nối tiếp (có lịch sử).

## 2. CN11 — Chuẩn hóa và viết lại câu hỏi (ưu tiên cao nhất)
- [ ] **Sửa lỗi (vẫn còn trên `dev`):** câu không dấu bị coi là ngoài phạm vi. `guardrails/` không đổi so với `main`; `DOMAIN_TERMS` trong `guardrails/patterns.py` chỉ có dạng có dấu; `check_scope` chạy trên câu gốc **trước** rewrite (`rag_chain.py:157`).
- [ ] Bước **chuẩn hóa** chạy **trước** kiểm tra phạm vi: NFC, viết thường, khoảng trắng, mở rộng viết tắt, xử lý không dấu.
- [ ] So khớp từ khóa phạm vi trên dạng bỏ dấu; khôi phục dấu cho truy vấn để vector/BM25 tìm đúng.
- [ ] Mở rộng từ điển viết tắt (hiện 7 mục trong `generation/query_rewriter.py` `ABBREVIATIONS`: đkhp, ctsv, bhyt, gpa, cpa, sv, gv) — thêm hp, tc, ktx, drl, ctđt, tn, gdtc, gdqp…; đưa ra file dữ liệu.
- [ ] ⚠️ Viết lại câu hỏi nối tiếp **theo luật** (Bộ chuẩn hóa không gọi Dịch vụ LLM — 2.7.1; đã trả lời hội đồng ở Q-3). Giữ `QUERY_REWRITE_USE_LLM=false`; viết lại bằng LLM là **hướng phát triển** (nếu bật thì Bộ kiểm soát phải xét cả câu gốc và câu viết lại).
- [ ] Cờ `NORMALIZATION_ENABLED`, `FOLLOW_UP_REWRITE_ENABLED`.
- [ ] Test: cặp có dấu/không dấu cho cùng kết quả phạm vi; hit@k/coverage@k có/không chuẩn hóa.
- [ ] 🆕 Lưu câu viết lại vào `messages.rewritten_question` (trả cho Ngọc) để soi lỗi khôi phục dấu.

## 3. CN12 — Truy xuất lai và xếp hạng lại
- [x] Hybrid pgvector + BM25 + RRF + gộp đoạn cha; BM25 chạy trên `search_text` (heading + nội dung, bảng tuần tự hóa "Cột: giá trị"); `bm25_norm_score` chuẩn hóa theo truy vấn.
- [x] Lọc theo dataset bật/tắt ở cả vector (`vectordb/pgvector_store.py`) và BM25 (`retrieval/bm25.py`).
- [ ] BM25 dùng **thư viện tách từ tiếng Việt** — hiện `_tokenize` vẫn `\w+` (`retrieval/bm25.py:175`, `retrieval/reranker.py:91`).
- [ ] **Cross-encoder mặc định** — hiện `RERANKER_PROVIDER=heuristic` (`core/config.py:170`, `.env.example`). Gate đã hỗ trợ ngưỡng cross-encoder; chỉ cần chọn model tiếng Việt, đưa vào Docker, đo thời gian tăng thêm.
- [ ] **Lọc hiệu lực** (QT3): chỉ lấy tài liệu `status = active` và chưa hết hạn (`documents.expiry_date`, `chunks.expiry_date`); trạng thái đọc từ CSDL cả cho đoạn chỉ có ở nhánh BM25, để chỉ mục BM25 cũ không làm lọt bản bị thay (Q-17).
- [ ] Lọc/ưu tiên theo đối tượng áp dụng (QT4, bảng `audiences`).
- [ ] 🆕 Ưu tiên nguồn chính thức: cộng trọng số cho đoạn có `documents.is_official` khi hợp nhất, **không lọc bỏ** (Q-32).
- [ ] 🆕 Lọc theo `chunks.chunk_strategy` của cấu hình đang chạy.
- [ ] Chế độ `RETRIEVAL_MODE = vector | bm25 | hybrid` cho **pipeline chat** (hiện chỉ có trong `scripts/eval_retrieval.py --mode`); đủ 3 cấu hình của Bảng 6 dòng 4.

## 4. Chia đoạn theo Điều/Khoản (cải tiến Bảng 6, dòng 3)
- [x] Chia theo Chương/Điều/Khoản/Điểm kể cả khi không có heading Markdown; Khoản/Điểm chỉ tách trong Điều; kế thừa số Khoản khi đánh số lại (`ingestion/chunker.py`, `ingestion/legal_units.py`); lọc nhiễu (`cleaner.py`).
- [x] Bảng không mất dữ liệu: nhận diện bảng LlamaParse, ghép bảng ngắt trang, giữ hàng.
- [x] Script kiểm tra: `check_chunks.py`, `check_structure.py`, `refresh_legal_metadata.py`, `refresh_search_text.py`.
- [ ] Gắn metadata nghiệp vụ cho đoạn: khóa/ngành (`audiences` cấp đoạn), năm học, ngày hết hạn của đoạn; nhóm tri thức và ngày ban hành lấy từ `documents`.
- [ ] 🆕 Ghi `start_offset`, `end_offset` của mỗi đoạn trên `extracted_text` đã lưu (bản scan: bản đã kiểm tra).
- [ ] ⚠️ `chunk_strategy = fixed | legal`: **lưu cả hai bộ đoạn** cho mỗi tài liệu trên cùng kho (UQ `document_id`, `chunk_strategy`, `chunk_index`); RAG cơ bản dùng `fixed`, vận hành dùng `legal`.
- [ ] 🆕 Không cắt giữa bảng hay danh sách bước của quy trình học vụ (Q-24).

## 5. CN10 — Trích xuất nội dung tài liệu
- [x] Parser `text`, `docling`, `llamaparse` (chọn tier fast / cost_effective / agentic / agentic_plus); chuẩn hóa heading dùng chung (`parsers/normalize.py`).
- [x] Tách bước **parse** và **chia đoạn**; lưu `documents.parsed_text`; admin sửa Markdown trước khi chia đoạn (Ngọc/đã có API + màn).
- [ ] OCR theo từng file — `DOCLING_OCR_ENABLED` vẫn toàn cục (mặc định tắt); hoặc quy ước dùng LlamaParse cho bản scan.
- [ ] Trạng thái `needs_review` cho bản scan (chặn chia đoạn tới khi admin duyệt, bất đồng bộ — 2.5.4 msg 12–16) — phối hợp Ngọc. Mọi tài liệu đều lưu `extracted_text` (≈ `parsed_text` của baseline).

## 6. CN13 — Bộ nhớ đệm: **Ngọc làm**
- [ ] Khánh chỉ cung cấp `prepare_query()` 🔗 — khóa cache = băm(câu đã viết lại, khóa, ngành) — và epoch đọc trước khi tìm kiếm (mục 0).

## 7. CN14 — Kiểm soát câu trả lời
- [x] Confidence gate hiệu chỉnh trên `bm25_norm`, vector, cross-encoder (`generation/confidence.py`; `scripts/eval_confidence.py`; báo cáo `documents/rag-eval/rag-18/`).
- [x] Câu từ chối không kèm nguồn; nhận diện câu từ chối biến thể của LLM (`generation/refusal.py`).
- [x] Không tự chèn citation; FE phân biệt nguồn được trích / nguồn liên quan.
- [ ] Phân loại và trả `answer_status` cho mọi nhánh (hiện có `guardrail_allowed`, `strong_context`, `confidence.reason` trong `retrieval_debug`).
- [ ] QT2: câu "không đủ căn cứ" kèm phòng ban (hiện chỉ "Chưa tìm thấy thông tin này trong tài liệu."). 🆕 Dùng **hai ngưỡng**: ngưỡng căn cứ (7) cao; ngưỡng chọn nhóm thấp hơn — đoạn cao nhất vượt ngưỡng nhóm thì lấy phòng ban của nhóm đó, không thì nhóm mặc định. Chọn cả hai trên tập điều chỉnh (Q-20).
- [ ] ⚠️ QT1: sau khi stream xong, kiểm `[n]` trỏ đúng một trong k đoạn; bỏ mã ngoài k đoạn; không còn mã hợp lệ → phát sự kiện **thay câu trả lời đã hiển thị** bằng thông báo không đủ căn cứ + phòng ban, `answer_status = no_context`, không lưu đệm (Q-26, Q-30).
- [ ] QT4: prompt nêu đối tượng áp dụng; chưa rõ khóa/ngành thì trình bày theo trường hợp.
- [ ] QT5: khuyến cáo đối chiếu văn bản gốc cho học phí, hạn nộp, tốt nghiệp.
- [ ] ⚠️ Yêu cầu theo Bảng 3: ngữ cảnh gửi LLM kèm tên văn bản, ngày ban hành, năm học, nhóm tri thức; lịch thi ghi ngày ban hành, học phí ghi năm học, học vụ ghi đơn vị xử lý (2.5.2 msg 27–28).

## 8. CN04 phía RAG — Câu hỏi liên quan
- [ ] Sinh 2–3 câu hỏi liên quan sau mỗi câu trả lời, trả qua event `related` 🔗.

## 9. Chỉ số chất lượng RAG
- [x] `scripts/eval_retrieval.py`: hit@1/4/10, MRR, coverage@k, section_dominance; 4 chế độ `bm25 | vector | hybrid | full`; cache embedding câu hỏi. Baseline ở `documents/rag-eval/baseline_*.json`.
- [ ] ⚠️ Recall@k, Precision@k, MRR theo **nhãn span**: đoạn liên quan = đoạn **chứa trọn** span; span cắt qua nhiều đoạn thì tính đoạn phủ phần lớn nhất; như nhau cho `fixed` và `legal`. Script gọi thẳng Bộ chuẩn hóa → Bộ truy xuất lai → Bộ xếp hạng lại để lấy k mã đoạn theo thứ tự (không qua API).
- [x] Ragas (`scripts/evaluate_ragas.py`) cho Faithfulness, Answer relevancy.
- [ ] Tỷ lệ đúng, tỷ lệ từ chối đúng end-to-end (gộp bộ 300 + 56).
- [ ] Ma trận cấu hình: RAG cơ bản (`fixed` + `vector`, tắt cờ khác) → bật lần lượt từng cải tiến (Bảng 6). Mỗi lần đổi cấu hình thì xóa `answer_cache`; không nạp tài liệu giữa các lượt đo.
- [ ] 🆕 Đo **tỷ lệ câu bị thay** sau sinh (QT1) trên tập kiểm tra — đã hứa với hội đồng ở Q-26.
- [ ] Số đo thời gian tăng thêm của cross-encoder (cho Ngọc).

## 10. Quyết định kỹ thuật cần chốt
- [ ] D1: LangChain (lớp `app/llm/` tự viết nay đã có retry, deadline, cache provider).
- [ ] D5: pyvi hay underthesea.
- [x] D7: dataset = nhóm tri thức → thiết kế dùng bảng `knowledge_groups` (thêm `department`, `contact`, `is_default`, `cache_epoch`).
- [ ] Model LLM, embedding, reranker cho thực nghiệm (chọn qua kho mô hình của admin; ghi vào quyển).

## 11. Đầu vào cho Chương 2 (review cho Ngọc)
- [ ] Nội dung 2.2.4 (CN10–CN14) — mô tả theo code đã có (chia Điều/Khoản, gate, parser).
- [ ] Review bảng `chunks` ở 2.6 và biểu đồ tuần tự 2.5.2–2.5.4 (bản đã Đạt hội đồng mô phỏng 2026-11-18; Khánh đọc lại để xác nhận khả thi).

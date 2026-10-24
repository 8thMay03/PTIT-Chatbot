# Implementation

- Task: `2026-10-24-rag-eval-retrieval-baseline`
- Cập nhật lúc: `2026-10-25T00:05:00+07:00`

## Thay đổi thực tế

- Mới `backend/scripts/eval_retrieval.py` (~530 dòng): CLI `--mode {bm25,vector,hybrid,full}`, `--dataset`, `--top-k` (mặc định 10), `--output`, `--embedding-cache`, `--limit`, `--compare A B`.
  - Chấm điểm thuần (tách hàm để unit test): `normalize_text` (NFKC → bỏ thẻ HTML → `html.unescape` → gộp khoảng trắng → casefold), `first_hit_rank` (khớp bất kỳ `expected_terms`), `compute_metrics` (hit@1/4/10 + MRR, làm tròn 6 chữ số), `aggregate_metrics` (overall + by_diacritics/by_question_type/by_source), `collect_metric_rows` cho bảng so sánh.
  - Tái dùng component của app, không sửa mã nguồn app: `BM25Search`, `create_vector_store`, `Retriever` (mode hybrid), `collapse_parent_results`, và cho `full`: `VietnameseQueryRewriter`, `VietnameseMultiQueryGenerator`, `fuse_multi_query_results`, `contains_prompt_injection`, `Reranker` (theo cấu hình).
  - `CachedEmbeddingModel`: bọc embedding model của app, cache vector theo `sha256(provider\x00model\x00text)`, ghi atomic (tmp + replace) ra `backend/storage/eval/embedding_cache.json` (thuộc vùng gitignore).
  - Warm-up: liệt kê trước các câu cần embed (mode vector/hybrid: câu hỏi; mode full: câu sau rewrite + biến thể theo luật) rồi gọi API theo lô 1 lần thay vì 100 lần từng câu.
  - Báo cáo JSON: `schema_version`, `mode`, `created_at`, `elapsed_seconds`, `git` (commit/branch/dirty — dirty chỉ tính file đã theo dõi), `dataset` (path/số câu/sha256), `embedding` (provider/model/thống kê cache), `corpus` (fingerprint = sha256 các `content_hash` sort theo id + số chunk/đã embed), `config` (22 trường settings RAG, không có secret), `eval`, `metrics`, `cases` (chi tiết rank trúng, term khớp, top-10 chunk).
- Mới `backend/tests/test_eval_retrieval.py`: 13 test thuần — import module khi đã xóa `OPENAI_API_KEY`/`OPENAI_COMPATIBLE_API_KEY`, chuẩn hóa NFKC/HTML/casefold, khớp nhiều term, hit@k/MRR (kể cả rỗng/trượt hết), nhóm dấu, nhóm metadata thiếu, cache hit/miss/persist/khóa theo model, nạp dataset (báo lỗi khi thiếu `expected_terms`).
- Mới `documents/rag-eval/`: `baseline_bm25.json`, `baseline_vector.json`, `baseline_hybrid.json`, `baseline_full.json`, `README.md` mô tả cách chạy + bảng baseline + cấu hình tại thời điểm đo + hạn chế.
- Mới trang task `.agents/tasks/2026-10-24-rag-eval-retrieval-baseline/` (5 file theo mẫu).

## Quyết định

- Mode `full` tái dựng `RagChain.retrieve_context` nhưng **bỏ guardrail scope** (không thuộc retrieval) và **bỏ lọc `strong_context`** (chỉ dùng khi chốt câu trả lời); giữ lọc prompt-injection trên context vì nằm trong pipeline trước khi đưa vào LLM.
- Tất cả mode đều `collapse_parent_results` về chunk cha: đây là text thật đưa vào LLM nên đo như vậy mới phản ánh hành vi app; hệ quả là số BM25 cao hơn phép đo ad-hoc trước đó (0,60/0,76/0,82/0,68) vốn so khớp trên chunk con.
- `hit@1/4/10` lấy từ prefix của cùng một lần chạy `top_k=10` (thực hành IR chuẩn, tránh 3 lần chạy riêng).
- Nhóm `by_question_type`/`by_source` đọc trường tùy chọn `question_type`, `source`/`source_document`/`document` trong dataset; thiếu thì `unknown` — sẵn sàng cho RAG-02 thêm metadata mà không đổi script.
- Cache embedding đặt trong `backend/storage/` (đã gitignore) để không commit vector; báo cáo chỉ đếm hit/miss.
- Cảnh báo trong `full` khi `query_rewrite_use_llm`/`multi_query_use_llm` bật: kết quả có thể không lặp lại được (LLM không tất định).

## Bàn giao

- Baseline 4 mode đã commit kèm cấu hình đầy đủ trong từng JSON (xem `verification.md`). Bước tiếp theo cho RAG-02: thêm câu không dấu + `question_type`/`source` vào dataset — script tự nhóm, không cần đổi mã.
- Không đổi `.env`/`.env.example`; baseline phản ánh cấu hình local hiện tại và đã ghi rõ trong `documents/rag-eval/README.md`.

## Trao đổi

- (không có — một agent tự thực hiện)

## Mở rộng 2026-10-25: coverage@k (AC-07)

- Người dùng hỏi có nên thêm recall/precision. Đánh giá ghi nhận: recall đáng thêm ngay dưới dạng **coverage@k** (69/100 câu có nhiều `expected_terms` nhưng hit chỉ cần khớp một); precision bằng `expected_terms` sẽ sai lệch (chunk liên quan nhưng không chứa chuỗi term bị tính false positive) — để dành cho Ragas context_precision hoặc khi RAG-02 gắn nhãn chunk vàng.
- Thay đổi trong `backend/scripts/eval_retrieval.py` (commit `2acff9660a83`):
  - `coverage_by_k`: tỉ lệ term được phủ bởi top-k (chuẩn hóa dùng lại `normalize_terms`/`normalize_text`; term trùng sau chuẩn hóa tính một lần).
  - `compute_coverage_metrics`: trung bình theo câu, câu thiếu coverage bị bỏ khỏi trung bình.
  - `aggregate_metrics` gộp coverage vào overall + từng nhóm; `run_case` ghi `coverage` từng câu; `print_summary` in 2 dòng (rank metrics + coverage).
  - `SCHEMA_VERSION` lên 2; `collect_metric_rows` chỉ giữ metric có thật trong báo cáo để `--compare` chéo v1/v2 hiển thị `—` thay vì 0 giả, kèm chú thích schema khác nhau.
- Test: 3 test mới (`coverage_by_k` từng case, `compute_coverage_metrics`, so sánh v1/v2), cập nhật 2 test cũ — 16/16 pass offline.
- Baseline chạy lại 4 mode tại commit `2acff9660a83`: hit/MRR và rank từng câu **giống hệt** bản 2026-10-24 (so với `git show HEAD~1`), chỉ thêm coverage — không hồi quy. Deterministic schema v2 kiểm chứng bằng 2 lần chạy bm25 (metrics + rank + coverage bằng tuyệt đối).

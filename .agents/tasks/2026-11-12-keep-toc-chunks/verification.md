# Verification: 2026-11-12-keep-toc-chunks

- Verifier: `claude-code`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `feat/keep-toc-chunks` trên `92aa804` (trước commit task).
- Môi trường: Windows 11, `backend/.venv` Python 3.11, Postgres docker `ptit_chatbot_postgres` (port 5433), `.env` local (CHUNK_SIZE 2048, CHILD_CHUNK_SIZE 1024, embedding `openai/text-embedding-3-small`).

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-code / `2026-11-12T23:12:00+07:00`.
- Loại: test tự động + chạy thử trên `parsed_text` D26 thật.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest tests/test_chunker.py -q`; script dump `documents.parsed_text` rồi `clean_text`.
- Kỳ vọng: section giữ nguyên, header `|Mục|Trang|`, entry viết lại, entry lạc vẫn lọc, idempotent.
- Kết quả thực tế: test xanh; với D26 cleaner giữ `# MỤC LỤC` + `|Mục|Trang|` + toàn bộ entry từ "Lời nói đầu|3" đến "Vui chơi, giải trí|268" (6.091 ký tự).
- Trạng thái: `passed`.
- Bằng chứng: các test `test_clean_text_keeps_compact_toc_table_with_synthetic_header`, `test_clean_text_keeps_toc_table_header_when_already_real`, `test_clean_text_rewrites_toc_dot_leader_entries`, `test_clean_text_rewrites_bold_page_toc_entries_inside_toc_only`, `test_clean_text_toc_rewrite_is_idempotent`, `test_clean_text_keeps_whole_toc_section_including_tables`, `test_clean_text_drops_toc_entries_with_two_dots` (entry lạc vẫn lọc).

### V-02 — AC-02

- Người thực hiện / thời gian: claude-code / `2026-11-12T23:13:00+07:00`.
- Loại: test tự động + kiểm tra index.
- Lệnh / thao tác: `pytest tests/test_document_pipeline.py -k toc`, `test_toc_tables_split_by_page_break_chunk_with_shared_header`; `python -m scripts.check_chunks` trên DB.
- Kỳ vọng: `is_toc` đúng; chunk mục lục có header; không vi phạm bất biến bảng; không bị báo nhiễu.
- Kết quả thực tế: test xanh; `check_chunks`: 1017 chunk, chỉ còn 1 cảnh báo có sẵn `chunk_starts_mid_word` ở `parent-0::child-0` ("logo: PTIT", chunk đầu tài liệu, không đổi so với trước); không có `noise_chunk` hay lỗi bảng. `find_table_coverage_issues` trên D26 trả `[]`.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra lệnh trong phiên.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-code / `2026-11-12T23:13:47+07:00`.
- Loại: kiểm tra DB sau khi chunk lại.
- Lệnh / thao tác: `ingestion_pipeline.chunk_document('e0997dd2…')`; `select count(*), count(embedding), sum(is_toc) from chunks`.
- Kỳ vọng: có chunk mục lục đủ entry, embed đủ.
- Kết quả thực tế: `1017 | 1017 | 7`; 7 chunk mục lục (chunk_index 7–13, 4 parent), chunk đầu bắt đầu "Mục: Lời nói đầu; Trang: 3" trong `search_text`, chunk cuối kết thúc "Vui chơi, giải trí|268".
- Trạng thái: `passed`.

### V-04 — AC-04

- Người thực hiện / thời gian: claude-code / `2026-11-12T23:14:16+07:00`.
- Loại: eval retrieval offline.
- Lệnh / thao tác: `python -m scripts.eval_retrieval --mode {bm25,hybrid}` trước/sau; `--compare`; phân tích `cases[].retrieved[].heading == "MỤC LỤC"`.
- Kỳ vọng: hit@4/hit@10 không giảm; không có hit nào đến từ chunk mục lục.
- Kết quả thực tế (`ptit_ragas_100`):

  | Chế độ | hit@1 | hit@4 | hit@10 | MRR |
  |---|---|---|---|---|
  | bm25 trước → sau | 0.710 → 0.700 | 0.830 → 0.830 | 0.890 → 0.890 | 0.769 → 0.764 |
  | hybrid trước → sau | 0.660 → 0.660 | 0.820 → 0.820 | 0.890 → 0.890 | 0.734 → 0.734 |

  bm25 đổi đúng 1 câu (`headquarters_address` rank 1 → 2); top-1 mới là "5. Kiểm tra những thông tin trong hợp đồng", không phải mục lục, nên chênh lệch đến từ thống kê BM25 (IDF) khi thêm 7 chunk. Mục lục không vào top-4 câu nào trong 100 câu; số hit đến từ chunk mục lục = 0.
  `ptit_rag_300` (chỉ có bản sau): bm25 hit@4 0.840, hybrid 0.827; mục lục vào top-4 ở 6 câu (bm25) / 5 câu (hybrid), đa số rank 3–4; số hit đến từ chunk mục lục = 0. Riêng `d26_g2_026` ("Mã chương trình CNTT Chất lượng cao") trượt top-10, mục lục ở rank 2 (hybrid); chưa xác minh câu này có trúng trên index cũ hay không.
- Trạng thái: `passed`.
- Bằng chứng: `documents/rag-eval/keep-toc/`.

### V-05 — AC-05

- Người thực hiện / thời gian: claude-code / `2026-11-12T23:16:00+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest tests/ -q`.
- Kết quả thực tế: `1340 passed, 24 skipped` (gồm test mới `test_chunk_records_flag_toc_chunks_and_serialize_toc_rows`).
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- `test_clean_text_keeps_every_pipe_line_on_d26_toc` bị skip vì `data/datasets/` không có file `.md` D26; hành vi tương ứng đã kiểm trên `parsed_text` từ DB (V-01).
- Chưa có baseline `ptit_rag_300` trên index cũ; chưa đo chế độ `vector`/`full`.
- Chưa kiểm tra end-to-end qua chat UI (container backend đã tự reload code mới qua volume mount).

## Kết luận

- Tiêu chí đã đạt: AC-01…AC-05.
- Tiêu chí chưa đạt/chưa xác minh: không có (xem giới hạn bên trên).
- Đề xuất: bàn giao review.

# Verification: 2026-11-05-table-search-context

- Verifier: `claude-code-agent`.
- Trạng thái tổng: `passed` (V-01…V-03; V-02 có ghi chú 1 câu nhiễu HNSW ở golden hybrid).
- Bản được kiểm tra: nhánh `feat/table-search-context` (nền `eeaf045`), working tree sau S-01…S-03
  ngày `2026-11-06` (commit của task ghi trong `review.md`).
- Môi trường: Windows 11, Python 3.11 (`backend/.venv`), chạy từ `backend/`; PostgreSQL + pgvector
  local (HNSW); mạng tới OpenAI hoạt động trong phiên này.

## Kiểm chứng tiêu chí

### V-01 — AC-01/AC-02 (đơn vị + D26)

- Người thực hiện / thời gian: `claude-code-agent` / `2026-11-06T22:52:59+07:00`.
- Lệnh / thao tác: `python -m pytest tests/test_table_search.py tests/test_refresh_search_text.py
  tests/test_document_pipeline.py tests/test_chunker.py tests/test_chunker_table_coverage.py
  tests/test_check_chunks.py tests/test_search_text.py -q -p no:cacheprovider -rs`.
- Kỳ vọng: test xanh; `text` không đổi, `search_text` chunk bảng có dạng `Cột: giá trị`; D26 chạy thật.
- Kết quả thực tế: 137 passed, 0 skipped (test D26 `test_data_file_d26_rows_are_serialized_with_context`
  chạy thật trên `data/`: >300 child bảng, không child nào còn dòng `|` trong thân `search_text`;
  hàng `||||ULO1.3` → `Phẩm chất người tốt nghiệp (Graduate Attributes): GA1; …`; hàng Trưởng khoa
  Cơ bản 1 → `ĐƠN VỊ: Lãnh đạo Khoa; HỌ VÀ TÊN: GS.TS. Phạm Ngọc Anh; CHỨC VỤ: Trưởng khoa;
  ĐIỆN THOẠI: 0912 316 141`). Trên DB: 720/2.020 chunk có `search_text` mới, `text` không đổi
  (script chỉ ghi khi `text` từng chunk khớp).
- Trạng thái: `passed`.
- Bằng chứng: `tests/test_table_search.py` (14), `tests/test_document_pipeline.py::test_chunk_records_serialize_table_rows_into_search_text_only`
  (+ `..._unchanged_without_tables`), `tests/test_refresh_search_text.py` (4).

### V-02 — AC-03/AC-04 (retrieval)

- Người thực hiện / thời gian: `claude-code-agent` / before `2026-11-06T22:36:28+07:00`…`22:37:00+07:00`,
  after `2026-11-06T22:48:24+07:00`…`22:48:36+07:00` (giờ trong JSON).
- Lệnh / thao tác: `python -m scripts.eval_retrieval --mode {bm25,hybrid} --dataset
  tests/fixtures/{ptit_ragas_100,table_questions}.json --output <abs>/documents/rag-eval/table-search-context/{before,after}_*.json`;
  giữa hai lần: `python -m scripts.refresh_search_text --apply`.
- Kỳ vọng: bảng bm25 hit@4 tăng, hybrid không giảm; golden hit@4/MRR không thấp hơn baseline đo lại.
- Kết quả thực tế (cùng index 2.020 chunk, fingerprint `d9bf102c…`):

  | Bộ / chế độ | hit@4 | MRR |
  |---|---|---|
  | Bảng bm25 | 0.857143 → 0.928571 | 0.857143 → 0.928571 |
  | Bảng hybrid | 0.785714 → 0.785714 | 0.738095 → 0.738095 |
  | Golden bm25 | 0.78 → 0.79 | 0.743302 → 0.745746 |
  | Golden hybrid | 0.74 → 0.73 | 0.708619 → 0.713952 |

  Câu đổi hạng: bảng bm25 `q_table_contact_truongkhoa` None→1; golden bm25 `student_card_return`
  5→3, `late_tuition_60_days` None→9; golden hybrid `summer_credit_limit` 4→3, `diploma_original`
  2→1, `process_grade_complaint` 4→5.
- Phân tích câu tụt (`process_grade_complaint`): hạng BM25 child của mọi chunk liên quan giống hệt
  trước/sau; hybrid tất định trên DB (chạy lại 2 lần giống hệt `after_hybrid.json`); chỉ mục vector
  HNSW — sau `UPDATE` 720 dòng, ANN đảo thứ tự hai bản sao `Điều 30` (exact #5/#6, ANN #6/#5), điểm
  RRF của bản hạng BM25 #1 giảm 0.01559 → 0.01540 (trước đó hơn hạng 5 chỉ ~0.00001).
  Đối chứng với vector chính xác (brute-force, cùng embedding), `search_text` cũ → mới: golden hybrid
  hit@4 0.74 → 0.74, MRR 0.709452 → 0.711119 (chỉ `english_four_skills` 3→2); bảng hybrid
  0.785714/0.738095 không đổi; `process_grade_complaint` hạng 4 ở cả hai.
- Trạng thái: `passed` — AC-03 đạt; AC-04 đạt theo điều kiện "chênh 1 câu do nhiễu phải chỉ ra từng
  câu và lý do" (golden hybrid −1 câu do HNSW, MRR tăng; riêng thay đổi `search_text` không làm tụt).
- Bằng chứng: `documents/rag-eval/table-search-context/{before,after}_*.json`, `README.md`; script
  đối chứng/mô phỏng ở scratchpad phiên (không thuộc repo).

### V-03 — AC-05

- Người thực hiện / thời gian: `claude-code-agent` / `2026-11-06T22:52:59+07:00`.
- Lệnh / thao tác: `python -m pytest -q -p no:cacheprovider` (từ `backend/`).
- Kỳ vọng: toàn bộ xanh.
- Kết quả thực tế: 802 passed, 1 skipped (`test_chunker_tables_benchmark.py` thiếu file benchmark
  thật — skip theo thiết kế). `tests/test_dataset_api.py::test_dataset_chunk_parse_validation`
  (rớt ngày `2026-11-06T21:17` do SSL) lần này pass — mạng tới OpenAI đã ổn. 803 test thu thập =
  783 trước đó + 20 test mới (14 + 2 + 4).
- Trạng thái: `passed`.
- Bằng chứng: output pytest full suite.

### V-04 — Không vi phạm bảng sau cập nhật index (phụ trợ AC-02)

- Lệnh / thao tác: `python -m scripts.check_chunks --db --strict`; `python -m scripts.refresh_search_text` (dry-run lại).
- Kết quả thực tế: 2 tài liệu / 2.020 chunk; 0 `table_row_*`, 0 `table_chunk_missing_header`,
  0 `search_text_missing_context`; 2 `chunk_starts_mid_word` (`logo: PTIT`) có từ trước → exit 1
  (đúng hành vi `--strict`). Dry-run lại: 0 chunk đổi (idempotent).
- Trạng thái: `passed`.

## Kiểm tra trạng thái — `2026-11-06T21:17:16+07:00`, `claude-code-agent` (lịch sử)

- Không có gì để kiểm chứng: working tree không có mã của task này (`grep serialize_table_row|table_search`
  trong `backend/app`, `backend/tests` không có kết quả; chưa có nhánh `feat/table-search-context`,
  chưa có `documents/rag-eval/table-search-context/`). `task.md` ở `draft`, S-01…S-03 `todo`,
  D-01/D-02 chưa được người dùng duyệt. V-01…V-03 giữ `not_run`.
- Lưu ý trước khi triển khai: index local hiện có 2 tài liệu / 2.020 chunk (khác index 1.010 chunk
  lúc đo `documents/rag-eval/table-chunking/after_*.json`), nên AC-03/AC-04 phải so với baseline
  đo lại trên index hiện tại, không dùng thẳng `after_*.json`. Máy hiện tại gọi OpenAI lỗi SSL
  (`CERTIFICATE_VERIFY_FAILED self-signed certificate`) — eval hybrid cần mạng ổn trước.

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-02, AC-03, AC-04 (kèm giải thích 1 câu nhiễu HNSW), AC-05.
- Tiêu chí chưa đạt/chưa xác minh: không có. Ngoài AC (ghi nhận): `q_table_ulo13` vẫn hụt; hybrid bảng không tăng.

# Báo cáo chunk lại + đo retrieval: table-chunking (S-07)

Nhánh: `feat/table-chunking-coverage` (tách từ `dev` tại `14c4eb6`).
Index local: 1 tài liệu được chunk (`e0997dd2`, dataset `default`, parsed_text từ
`data/Sổ tay sinh viên D26 _1_.pdf`, 584.982 ký tự), tài liệu còn lại
(`7b99bad5`, dataset `0ae10990`) đã parse nhưng chưa chunk từ trước.

Cấu hình chunk: `parent_size=2048/overlap=256`, `child_size=1024/overlap=128`,
`min_child_chars=120`, `parent_child_chunking_enabled=true`.
Embedding: `openai text-embedding-3-small` (trường `text`).

## Ước lượng trước khi chunk lại (S-07)

- Dry-run trên parsed_text trong DB: **1.010 chunk mới** (cũ 1.013),
  ~117.000 từ (~150K token, chi phí embedding không đáng kể).
- Chunk lại bằng `IngestionPipeline.chunk_documents(dataset_id="default")`
  (đọc `parsed_text` đã lưu, không parse lại, không tốn credit LlamaParse).

## Chất lượng chunk trên file D26 (LlamaParse `.md`, 3.653 hàng bảng)

| Chỉ số | Trước (dev) | Sau |
|---|---|---|
| Khối bảng Markdown nhận diện | 0 | 400 (424 khối compact, 24 mảnh ngắt trang được gộp) |
| Mảnh `\|…\|` xử lý như văn xuôi | 424 | 0 |
| Số child | 1.002 | 1.010 |
| Dòng hàng bị cắt dở trong child | 32–49 | 0 |
| Hàng không nguyên vẹn trong child nào | 2 | 0 |
| Child có hàng nhưng thiếu header | 49 | 0 |
| Độ dài child p50 / p95 / max | 585 / 994 / 1.024 | 571 / 998 / 1.868 |

`check_chunks --data ../data` (10 tài liệu: `.md` LlamaParse + `.pdf` Docling/DOCX):
0 vi phạm bảng (trước sửa: 6 missing + 4 broken trên bản parse Docling).
Còn 1 finding `chunk_starts_mid_word` (`logo: PTIT`) có từ trước, không liên quan bảng.
`check_chunks --db` sau chunk lại: 0 vi phạm bảng.

## Retrieval trước/sau (cùng index local, cùng câu hỏi)

Lệnh: `python -m scripts.eval_retrieval --mode {bm25,hybrid} [--dataset ...]
--output documents/rag-eval/table-chunking/{before,after}_*.json`.

Corpus: trước `4c60e512…` (1.013 chunk) → sau `7e881bf5…` (1.010 chunk).

### Golden `ptit_ragas_100.json` (100 câu)

| Chế độ | hit@4 trước → sau | MRR trước → sau |
|---|---|---|
| bm25 | 0.830 → 0.830 | 0.767762 → 0.767762 (giống hệt) |
| hybrid | 0.830 → 0.820 | 0.734611 → 0.734111 |

Một câu duy nhất đổi hạng hybrid (`student_card_validity` 4→5): cùng tập
parent theo cùng thứ tự, chỉ hoán đổi hạng 4/5 giữa hai context đều chứa cụm
từ chung chung `thời gian học tập` — nhiễu ngưỡng top-4, không phải suy giảm
chất lượng (nội dung truy xuất giữ nguyên).

### Bộ câu hỏi về bảng `table_questions.json` (14 câu, fixture mới)

| Chế độ | hit@4 trước → sau | MRR trước → sau |
|---|---|---|
| bm25 | 0.857 → 0.857 (12/14) | 0.866071 → 0.866071 (giống hệt) |
| hybrid | 0.786 → 0.786 (11/14) | 0.783333 → 0.776984 |

Câu hụt bm25 (`q_table_ulo13` ngoài top-10, `q_table_contact_truongkhoa` hạng 8)
và hai câu tụt hạng hybrid (`q_table_ulo13` 5→6, `q_table_drl_vanghop` 6→9) đều
là vấn đề **thứ hạng BM25/vector**, không phải mất hàng: các hàng liên quan đã
nguyên vẹn trong index nhưng chunk chứa hàng không vào được top-k (vd. con trỏ
`ULO1.3` xếp hạng ~#45 BM25 vì query nhiều từ phổ biến lấn át từ hiếm; các trang
liên hệ 8 khoa cùng khớp `Trưởng khoa` + số điện thoại).

## Kết luận và việc tiếp theo

- Toàn vẹn hàng bảng: đạt (0 vi phạm trên mọi định dạng parse, mọi test xanh).
- Không thụt lùi golden set: đạt về thực chất (bm25 giống hệt; hybrid chênh
  1 câu do nhiễu ngưỡng, nội dung truy xuất không đổi).
- hit@4 bộ câu hỏi bảng cao hơn baseline: **chưa đạt** — chunk nguyên vẹn là
  điều kiện cần nhưng chưa đủ để tăng hạng; cần làm giàu `search_text` của
  chunk bảng (điền ô trống từ hàng trên, tuần tự hóa `Cột: giá trị`) để BM25
  thấy được hàng — xem task tiếp theo `2026-11-05-table-search-context` (D-01).

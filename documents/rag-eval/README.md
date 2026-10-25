# Baseline đánh giá retrieval offline

Bộ đánh giá retrieval riêng (không sinh câu trả lời, không cần LLM judge) để đo
nhanh sau mỗi thay đổi về chunking, index hoặc cấu hình hybrid/rerank.

Script: [`backend/scripts/eval_retrieval.py`](../../backend/scripts/eval_retrieval.py) ·
Dataset: [`backend/tests/fixtures/ptit_ragas_100.json`](../../backend/tests/fixtures/ptit_ragas_100.json) (100 câu, sha256 `fa9d2d64f4045c0f…`)
Unit test: [`backend/tests/test_eval_retrieval.py`](../../backend/tests/test_eval_retrieval.py)

## Cách chạy

```powershell
cd backend
python -m scripts.eval_retrieval --mode bm25    # hoặc vector | hybrid | full
python -m scripts.eval_retrieval --compare ..\documents\rag-eval\baseline_bm25.json ..\documents\rag-eval\baseline_hybrid.json
```

- Chỉ số:
  - **hit@1 / hit@4 / hit@10 và MRR** — theo rank context đầu tiên chứa một `expected_terms`;
  - **coverage@1/4/10** — tỉ lệ `expected_terms` được phủ bởi top-k (recall theo term), đo việc truy xuất **đủ** thông tin cho câu trả lời thay vì chỉ trúng một.
  - **section_dominance** (từ schema v3) — tỉ lệ câu có mỗi section (`source_name` + `section_path`) trong top-4; `--compare` tự tính lại từ `heading` cho báo cáo cũ.
  - "Trúng" khi một `expected_terms` xuất hiện trong text context sau chuẩn hóa NFKC + bỏ thẻ HTML
  + casefold — nhãn không phụ thuộc chunk ID nên vẫn dùng được khi đổi chunking.
- Embedding câu hỏi được cache tại `backend/storage/eval/embedding_cache.json`
  (khóa = provider + model + text) nên chạy lại không tốn API.
- Mỗi báo cáo JSON tự ghi: snapshot cấu hình RAG, model embedding, fingerprint kho
  tài liệu, git commit, thời điểm chạy và chi tiết từng câu.

## Baseline 2026-10-25

Index hiện tại: 1 tài liệu "Sổ tay sinh viên D26" (1269 chunk, embed đủ), fingerprint `ccf48780bbcc813d…`.
Commit `2acff9660a83` (bản có coverage@k; hit/MRR không đổi so với bản đo tại `bdff20ba3148`), nhánh `dev`. Chạy trên `.env` local (khác `.env.example`).

| Chế độ | hit@1 | hit@4 | hit@10 | MRR | cov@1 | cov@4 | cov@10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25 | **0.690** | 0.830 | **0.900** | **0.755** | **0.637** | 0.797 | **0.866** |
| vector | 0.590 | 0.800 | 0.870 | 0.688 | 0.530 | 0.749 | 0.826 |
| hybrid | 0.650 | **0.840** | **0.900** | 0.739 | 0.593 | **0.799** | 0.858 |
| full | 0.620 | 0.830 | **0.900** | 0.722 | 0.568 | 0.793 | 0.858 |

Cấu hình đáng chú ý tại thời điểm đo (lấy từ `config` trong từng báo cáo):

- Chunking: parent 2048/overlap 256, parent-child bật, child 1024/overlap 128.
- Hybrid: `HYBRID_VECTOR_WEIGHT=0.80`, candidate multiplier 4, RRF k=60.
- Multi-query và reranker đang **tắt**; query rewrite theo luật (không LLM).
- Embedding: OpenAI `text-embedding-3-small` (1536 chiều).
- `full` = hybrid + query rewrite theo luật; vì multi-query/rerank tắt nên khác
  biệt chính so với `hybrid` là câu hỏi được chuẩn hóa (casefold, bỏ lời dẫn)
  trước khi embed.

Đọc số:

- BM25 đơn thuần đang dẫn đầu hit@1/MRR **và** coverage trên bộ câu này; vector là
  thành phần yếu nhất. Hybrid với trọng số vector 0.80 bị vector kéo xuống hit@1
  (0.650 < 0.690 của BM25) nhưng lại tốt nhất ở hit@4 — hạ `HYBRID_VECTOR_WEIGHT`
  là thí nghiệm đáng làm đầu tiên.
- Khoảng cách hit@4 (0.84) với coverage@4 (0.80) của hybrid cho thấy: câu trúng
  thường vẫn thiếu một phần thông tin trong top-4 — với câu hỏi cần nhiều dữ kiện,
  LLM có thể trả lời thiếu dù retrieval "đạt". Tăng top_k hoặc multi-query là hai
  hướng xử trực tiếp khoảng trống này.
- Hai lần chạy liên tiếp cùng cấu hình cho kết quả giống hệt nhau (kể cả thứ tự
  chunk, điểm số và coverage); hybrid chạy ~4.5–5.5s với cache embedding nóng.

## RAG-05 — chuẩn hóa phân cấp heading (2026-10-25)

Báo cáo: [`rag-05/`](rag-05/) (schema v3: thêm `retrieved[].section_path` và
`metrics.section_dominance`, tức tỉ lệ câu có mỗi section trong top-4). Cấu hình RAG giữ
nguyên như baseline; chỉ đổi Markdown đầu vào nhờ bước `normalize_markdown` chạy sau mọi
parser (PHẦN=1, tiêu đề văn bản=2, Chương=3, Mục=4, Điều=5).

| Bản D26 | Chế độ | hit@1 | hit@4 | hit@10 | MRR | cov@4 | cov@10 | section chiếm chỗ nhất (top-4) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| baseline (processed, chưa chuẩn hóa) | hybrid | 0.650 | 0.840 | 0.900 | 0.739 | 0.799 | 0.858 | 0.45 "2. Khóa học" |
| **processed + chuẩn hóa** (chọn) | hybrid | **0.720** | **0.850** | 0.900 | **0.780** | **0.807** | 0.853 | **0.15** "Điều 25. Thang điểm đánh giá" |
| Docling + chuẩn hóa | hybrid | 0.680 | 0.850 | 0.890 | 0.763 | 0.792 | 0.835 | 0.16 "Điều 25. Thang điểm đánh giá" |
| baseline (processed, chưa chuẩn hóa) | bm25 | 0.690 | 0.830 | 0.900 | 0.755 | 0.797 | 0.866 | 0.42 "2. Khóa học" |
| processed + chuẩn hóa | bm25 | 0.700 | 0.830 | 0.890 | 0.762 | 0.797 | 0.851 | 0.15 "Điều 12. Đăng ký học tập" |
| Docling + chuẩn hóa | bm25 | 0.730 | 0.840 | 0.890 | 0.786 | 0.803 | 0.846 | 0.15 "3. Khối lượng học tập" |

- Index: processed 1283 chunk (fingerprint `0a63b72686b2…`), Docling 1038 chunk
  (`86e726a7316d…`). Đo trên working tree chưa commit, nền commit `9d67b581ee6d`.
- **Bản chuẩn cho D26: `data/processed/Sổ tay sinh viên D26 _1_ _1_.md` (parser `text`).**
  Bản này tốt hơn Docling ở chế độ hybrid (chế độ app dùng) trên mọi chỉ số, đạt ngưỡng
  chiếm chỗ ≤ 15%. Văn bản Docling còn lỗi thứ tự đọc: tiêu đề Nghị định 238 dính đoạn
  "Lắng nghe giảng viên…", Điều 16 đứng trước Điều 12. Docling chỉ nhỉnh hơn ở BM25
  thuần (hit@1 0.730).
- So với baseline hybrid: 3 câu có thêm hit@4 (`intensive_course_limit`,
  `grade_improvement_rule`, `student_card_return`) và 2 câu mất
  (`student_card_initial_deadline` rank 1→7, `exam_review_form_destination` rank 3→ngoài
  top-10). Trường hợp thứ hai là do Điều 30 trước đây nằm chung section "Điều 26"; giờ
  nó là section riêng nên không còn được kéo theo. coverage@10 giảm nhẹ (0.858→0.853).
- Ingest lại làm chỉ mục vector xấp xỉ được dựng lại, nên các rank 5–10 có thể xê dịch
  giữa hai lần ingest cùng nội dung (lần đo này: coverage@10 0.850 so với 0.853; hit@1/4
  và MRR không đổi). Trên cùng một index, chạy lại vẫn cho kết quả giống hệt.
- Kiểm tra cấu trúc: `python -m scripts.check_structure <file> [--parser docling] --tree --strict`.

## RAG-06 — chunking Điều/Khoản, `search_text`, lọc nhiễu (2026-10-25)

Báo cáo: [`rag-06/`](rag-06/) (cùng schema v3; thí nghiệm A/B ở
[`rag-06/experiments/`](rag-06/experiments/)). Thay đổi đầu vào index so với RAG-05:

- **Chunking theo Điều/Khoản**: parent = một Điều/mục (Điều dài thì nhóm Khoản liên
  tiếp), child = Khoản/đoạn; cắt đoạn dài theo ranh giới câu, gộp chunk < 120 ký tự
  vào chunk liền kề cùng section (`MIN_CHILD_CHUNK_CHARS`). Vẫn dùng cấu hình local
  2048/1024 trong `.env`.
- **`search_text`** = `"{tên tài liệu} > {section_path}\n{text}"` (cột mới qua
  migration `0003`); **BM25 tokenize `search_text`**; embedding đọc trường theo
  `EMBEDDING_INPUT_FIELD` (mặc định `text` — xem ghi chú dưới).
- **Lọc nhiễu** trong cleaner: mục lục (cả section, kể cả bảng), quốc hiệu + tiêu ngữ,
  dòng ngày tháng, số trang, khối chữ ký + "Nơi nhận", watermark scan. Script kiểm tra
  mới: `python -m scripts.check_chunks --db | --data <dir> [--strict]`.

Index: 1203 chunk / 749 parent (fingerprint `620d26fd0e0c…`), chi phí re-embed ~$0.007.

| Chế độ | hit@1 | hit@4 | hit@10 | MRR | cov@4 | so với RAG-05 |
|---|---:|---:|---:|---:|---:|---|
| hybrid (RAG-06) | 0.720 | **0.850** | 0.890 | **0.778** | 0.804 | ngang (RAG-05: 0.850/0.780) |
| bm25 (RAG-06) | 0.710 | **0.850** | **0.910** | **0.770** | 0.798 | **+0.02 hit@4** (0.830/0.762) |
| vector (RAG-06) | 0.620 | 0.770 | 0.850 | 0.700 | 0.727 | hit@4 −0.03, MRR +0.01 (0.800/0.688) |

Đọc số và quyết định:

- **Header ngữ cảnh giúp BM25** (term như "BHYT" giờ nằm trong text được tokenize) nhưng
  **làm vector tụt** khi embed thẳng: thí nghiệm embed `search_text` cho hybrid
  0.820/0.738 (thấp hơn cả RAG-05) vì header tĩnh dài, nhiều chữ HOA làm vector
  `text-embedding-3-small` lệch. Vì vậy mặc định `EMBEDDING_INPUT_FIELD=text` — embedding
  dùng text hiển thị, BM25 dùng `search_text`; muốn bật lại cho model khác chỉ cần đổi env.
- **Chưa đạt tiêu chí "hybrid tăng"**: hybrid ngang bằng RAG-05 (chênh MRR −0.002, trong
  sai số hai lần ingest đã ghi nhận ở RAG-05), nhóm 18 câu thủ tục giảm hit@4
  0.667 → 0.611 — 3 câu thua đều nằm ở guide "HƯỚNG DẪN THỦ TỤC HÀNH CHÍNH" mà parent
  theo mục làm evidence phân mảnh. Hướng xử lý tiếp: parent lớn hơn cho tài liệu guide,
  tune `HYBRID_VECTOR_WEIGHT`, hoặc contextual embedding bằng LLM.
- Chất lượng ngữ liệu: 0 chunk mục lục/quốc hiệu/chữ ký (index RAG-05 còn 4 chunk "MỤC
  LỤC"), 0 chunk cắt giữa từ (trước: 143), 0 chunk < 120 ký tự ngoài section ngắn thật
  (trước: 59). `check_chunks --db --strict` sạch.

## Hạn chế đã biết

- Dataset chưa có metadata `question_type` / `source` nên các nhóm
  `by_question_type`, `by_source` hiện toàn `unknown`; 100/100 câu đều có dấu nên
  nhóm `by_diacritics` mới chỉ có `co_dau`. RAG-02 bổ sung dữ liệu sẽ điền các nhóm này.
- Các số Ragas 0.90/0.95/0.93/0.85 trong README chính đo bằng pipeline kèm sinh
  câu trả lời (LLM judge), không so sánh trực tiếp với các số retrieval thuần ở đây.

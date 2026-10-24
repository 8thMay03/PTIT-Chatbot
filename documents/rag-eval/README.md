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

## Hạn chế đã biết

- Dataset chưa có metadata `question_type` / `source` nên các nhóm
  `by_question_type`, `by_source` hiện toàn `unknown`; 100/100 câu đều có dấu nên
  nhóm `by_diacritics` mới chỉ có `co_dau`. RAG-02 bổ sung dữ liệu sẽ điền các nhóm này.
- Các số Ragas 0.90/0.95/0.93/0.85 trong README chính đo bằng pipeline kèm sinh
  câu trả lời (LLM judge), không so sánh trực tiếp với các số retrieval thuần ở đây.

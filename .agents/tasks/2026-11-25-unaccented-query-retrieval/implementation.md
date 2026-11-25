# Implementation: 2026-11-25-unaccented-query-retrieval

## Tổng quan triển khai

Nhánh `feat/unaccented-query-retrieval` (tách từ `dev` tại `b8c2ff3`). S-01, S-02 xong; S-03 … S-05 chưa bắt đầu. Gate chưa đổi nên câu không dấu vẫn trượt gate.

## Nhật ký theo nhiệm vụ

### S-01 — agent-backend

- Cập nhật lúc: `2026-11-25T21:30:00+07:00`.
- Đã làm:
  - `scripts/typo_variants.py`: thêm chế độ `strip_partial` vào `PERTURB_MODES`; `perturb_question(..., "strip_partial", seed, id)` bỏ dấu một nửa số chữ có dấu (rng theo seed + id như `typo`). Câu có dưới hai chữ có dấu giữ nguyên, `applied=[]` (thực tế 376/376 câu của 3 fixture đều áp được).
  - `scripts/eval_confidence.py`, `scripts/eval_retrieval.py`: ghi `perturb.seed` cho cả `strip_partial`; cập nhật docstring/help.
  - Test: `tests/test_typo_variants.py` thêm `test_perturb_question_strip_partial_mode`, `test_strip_partial_set_on_golden_fixture_keeps_mixed_accents`.
  - Đo nền `eval_confidence` 3 fixture × `none|strip_all|strip_partial|typo` và `eval_retrieval` `bm25|vector|hybrid` × `none|strip_all|strip_partial` trên `ptit_rag_300`. Kết quả + lệnh: `documents/rag-eval/unaccented-query/README.md`.
- File thay đổi: `backend/scripts/typo_variants.py`, `backend/scripts/eval_confidence.py`, `backend/scripts/eval_retrieval.py`, `backend/tests/test_typo_variants.py`, `documents/rag-eval/unaccented-query/{README.md,baseline_*.json}`; commit: xem `git log` của nhánh.
- Quyết định:
  - 9 báo cáo `eval_retrieval` (~2 MB/file, 18 MB) chỉ dùng chẩn đoán nên để ở `backend/storage/eval/unaccented-query/` (git ignore), số liệu ghi trong README; chỉ commit 4 báo cáo `baseline_*.json` (4.3 MB) mà S-03 cần để so sánh.
  - Corpus hiện tại 993 chunk (task query-correction đo trên 1017): dùng baseline mới làm mốc cho mọi AC.
- Phát hiện ảnh hưởng S-02/S-03: nhánh vector riêng cũng sụp với câu bỏ dấu (hit@4 226 → 51) dù cosine vẫn vượt ngưỡng 0.37 ở 289/300. BM25 bỏ dấu một mình có thể chưa đủ cho AC-03 về hit@4; đã ghi vào Rủi ro trong `plan.md` (đo thêm giảm trọng số vector cho câu bỏ dấu, khả năng cao cần S-04).
- Kiểm tra đã chạy: xem `verification.md` V-01.
- Còn lại/blocker: không có. Lưu ý `eval_retrieval --output` tương đối tính từ gốc repo (không phải `backend/`).

### S-02 — agent-backend

- Cập nhật lúc: `2026-11-25T21:39:17+07:00`.
- Đã làm:
  - `retrieval/bm25.py`: `_tokenize_folded` (= `_tokenize(strip_accents(text))`); `_ensure_index` dựng thêm `BM25Okapi` bỏ dấu trên cùng snapshot, cùng vô hiệu theo `invalidate_bm25_cache`. `search()` luôn tính điểm chỉ mục có dấu; chuyển sang xếp theo chỉ mục bỏ dấu khi câu không có dấu (`has_accents` sai) hoặc top-1 `bm25_norm_score` có dấu (trong tập dataset được lọc) dưới `settings.retrieval_min_bm25_norm_score`. Kết quả thêm `bm25_folded_norm_score` (`None` khi xếp theo chỉ mục có dấu) và `bm25_index`; `score` là điểm thô của chỉ mục xếp hạng; `bm25_norm_score` luôn theo chỉ mục có dấu (0.0 nếu chunk không khớp chỉ mục có dấu).
  - `retrieval/hybrid.py`: mang `bm25_folded_norm_score`, `bm25_index` từ nhánh keyword. `retrieval/parent_child.py`, `retrieval/multi_query.py`: max `bm25_folded_norm_score`; `bm25_index` đi theo kết quả được giữ (child đầu tiên / kết quả điểm cao nhất).
  - `retrieval/reranker.py` `heuristic_rerank`: câu không dấu tính `term_coverage` trên token bỏ dấu.
  - Test: `tests/test_bm25_folded.py` (9 test: khớp không dấu, `đ`, câu có dấu giữ thứ hạng = `rank_bm25`, fallback khi dưới ngưỡng, ngưỡng điều khiển fallback, lọc dataset, rebuild sau invalidate, các bước gộp, heuristic rerank). `tests/test_bm25_normalized.py::test_normalized_score_stays_in_unit_interval` đặt ngưỡng 0 vì câu của test (top-1 0.21) nay chuyển sang chỉ mục bỏ dấu, nơi `bm25_norm_score` không còn đơn điệu theo thứ hạng.
- File thay đổi: `backend/app/retrieval/{bm25,hybrid,multi_query,parent_child,reranker}.py`, `backend/tests/test_bm25_folded.py`, `backend/tests/test_bm25_normalized.py`.
- Quyết định/giao diện: hợp đồng trường kết quả đúng như `plan.md`; `parent_child.py` thêm vào phạm vi S-02. Chưa đưa trường mới vào `rag_chain._debug_chunk` và `eval_confidence` (S-03/S-05).
- Số đo kiểm tra nhanh (chưa đổi gate; báo cáo tạm ở `backend/storage/eval/unaccented-query/s02_*.json`, không commit), `ptit_rag_300` hit@4:

  | | trước S-02 | sau S-02 |
  |---|---|---|
  | `eval_retrieval --mode bm25`, có dấu / bỏ dấu / bỏ dấu một phần | 255 / 46 / 212 | 255 / **240** / **240** |
  | `eval_retrieval --mode hybrid`, có dấu / bỏ dấu / bỏ dấu một phần | 244 / 64 / 188 | 244 / 93 / 193 |
  | `eval_confidence` (pipeline luật), có dấu / bỏ dấu / bỏ dấu một phần / lỗi gõ | 250 / 50 / 173 / 210 | 250 / 67 / 179 / 213 |

  Qua gate không đổi ở mọi bộ (gate chưa đọc tín hiệu bỏ dấu). Bản có dấu: gate 282, hit@4 250, câu không đáp án 8/12/0 như baseline; 13 câu (2 câu `ptit_rag_300`, 11 câu `ptit_no_answer_56`) đổi danh sách chunk vì đều dưới ngưỡng nên chuyển chỉ mục, cả 13 vẫn trượt gate và giữ nguyên rank trúng.
- Nhận định cho S-03: BM25 bỏ dấu gần bằng bản có dấu, nhưng RRF với `hybrid_vector_weight=0.8` để nhánh vector (sai với câu bỏ dấu) quyết định thứ hạng. S-03 cần đo giảm trọng số vector khi `bm25_index == folded` trước khi chọn ngưỡng; S-04 vẫn có thể cần.
- Kiểm tra đã chạy: `pytest` backend toàn bộ `1695 passed, 24 skipped`; test retrieval liên quan `48 passed`.
- Còn lại/blocker: không có.

## Trao đổi giữa agents

Chưa có.

## Bàn giao

Chưa có.

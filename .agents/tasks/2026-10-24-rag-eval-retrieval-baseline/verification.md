# Verification

- Task: `2026-10-24-rag-eval-retrieval-baseline`
- Cập nhật lúc: `2026-10-25T00:05:00+07:00`
- Môi trường: Windows, `backend/.venv` (Python 3.11), PostgreSQL pgvector 127.0.0.1:5433, index 1 tài liệu / 1269 chunk đã embed, nhánh `dev` tại `bdff20ba3148`.

## AC-01 — hybrid 100 câu dưới 60 giây khi có cache embedding

- Lệnh: `python -m scripts.eval_retrieval --mode hybrid` (backend, dataset mặc định `tests/fixtures/ptit_ragas_100.json`).
- Kết quả: `passed`.
  - Lần 2 (cache nóng, 200 hit / 0 miss): `elapsed=4.563s`, tổng thời gian quy trình `real 0m5.111s` — dưới 60 giây với dư địa lớn.
  - Lần 1 (cache lạnh, gọi 1 lô API embedding): `real 0m10.426s`.

## AC-02 — hai lần chạy liên tiếp cho kết quả giống hệt nhau

- Lệnh: chạy `--mode hybrid` hai lần (bản 2 ghi ra file tạm), so sánh bằng Python: `metrics` bằng nhau tuyệt đối; duyệt 100 câu so `first_hit_rank`, `matched_term`, và toàn bộ `retrieved` (chunk_id + score theo thứ tự).
- Kết quả: `passed` — `metrics: GIỐNG HỆT; chênh lệch từng câu: 0 / 100`.

## AC-03 — báo cáo JSON chứa đủ cấu hình, model embedding, fingerprint kho, commit, chỉ số tổng và theo nhóm

- Kiểm tra nội dung `documents/rag-eval/baseline_hybrid.json` (các bản khác cùng schema): `config` đủ 22 trường (chunk 2048/256, child 1024/128, `hybrid_vector_weight` 0.8, multiplier 4, RRF k 60, multi-query/reranker tắt…); `embedding.model=text-embedding-3-small` + thống kê cache; `corpus.fingerprint=ccf48780bbcc813d…` (1 tài liệu, 1269 chunk, 1269 đã embed, kèm method); `git.commit=bdff20ba3148…`, branch `dev`; `metrics.overall` + `by_diacritics` / `by_question_type` / `by_source`; `cases` có rank trúng, term khớp, top-10 chunk.
- Kết quả: `passed`.

## AC-04 — baseline đủ 4 chế độ trên index hiện tại, commit kèm mô tả cấu hình

- Bốn file `documents/rag-eval/baseline_{bm25,vector,hybrid,full}.json` cùng corpus fingerprint `ccf48780bbcc813d…`, cùng dataset (sha256 `fa9d2d64f4045c0f…`), cùng commit `bdff20ba3148`; `documents/rag-eval/README.md` mô tả bảng số + cấu hình tại thời điểm đo + hạn chế nhóm.
- Số liệu overall:

  | mode | hit@1 | hit@4 | hit@10 | MRR | elapsed |
  |---|---:|---:|---:|---:|---:|
  | bm25 | 0.690 | 0.830 | 0.900 | 0.755 | 1.9s |
  | vector | 0.590 | 0.800 | 0.870 | 0.688 | 3.6s |
  | hybrid | 0.650 | 0.840 | 0.900 | 0.739 | 9.9s (lần đầu, kèm gọi API warm cache) |
  | full | 0.620 | 0.830 | 0.900 | 0.722 | 6.6s |
- Kết quả: `passed` (bằng chứng commit bổ sung sau khi commit mã + báo cáo).

## AC-05 — unit test phần chấm điểm chạy offline, không cần OPENAI_API_KEY

- Lệnh: `pytest tests/test_eval_retrieval.py -q`.
- Kết quả: `passed` — 13 passed trong 0.19s. Test `test_module_imports_without_api_key` xóa biến `OPENAI_API_KEY`/`OPENAI_COMPATIBLE_API_KEY` rồi reload module; các test còn lại chỉ dùng hàm thuần và fake embedding model, không mở kết nối mạng/DB.
- Bộ suite đầy đủ `pytest tests/ -q`: 247 passed, 1 skipped, 0 failed — không hồi quy.

## AC-06 — `--compare` in bảng chênh lệch

- Lệnh: `python -m scripts.eval_retrieval --compare ..\documents\rag-eval\baseline_bm25.json ..\documents\rag-eval\baseline_hybrid.json` và cặp `baseline_vector.json` vs `baseline_full.json`.
- Kết quả: `passed` — bảng in đủ `overall` + từng nhóm, cột A/B/delta (ví dụ overall hit@1 0.690 → 0.650, delta −0.040); cảnh báo khi fingerprint/dataset khác nhau đã có nhánh xử lý (hai bản này giống nhau nên không in cảnh báo).

## Kiểm tra chưa chạy

- Không chạy `--compare` trên hai báo cáo khác corpus/dataset thật (chỉ xem mã nhánh cảnh báo); chưa đo trên chế độ `full` với multi-query/reranker bật vì cấu hình hiện tại tắt.

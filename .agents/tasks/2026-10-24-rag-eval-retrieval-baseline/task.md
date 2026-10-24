# Task: Dựng bộ đánh giá retrieval offline và chốt baseline

- ID: `2026-10-24-rag-eval-retrieval-baseline`
- Trạng thái: `done`
- Coordinator: `zcode-agent`
- Người yêu cầu: người dùng (phiên ZCode 2026-10-24)
- Tạo lúc: `2026-10-24T23:54:57+07:00`
- Cập nhật lúc: `2026-10-25T00:15:00+07:00`

## Yêu cầu và kết quả mong muốn

- Hiện chỉ có `scripts/evaluate_ragas.py` (chậm, tốn phí, cần LLM judge) và `scripts/evaluate.py` (chạy cả RAG chain lẫn LLM). Chưa có cách đo nhanh riêng phần retrieval sau mỗi thay đổi về chunking hoặc index.
- Báo cáo Ragas chỉ lưu `top_k`, không lưu cấu hình hay phiên bản kho tài liệu, nên không biết các số 0,90 / 0,95 / 0,93 / 0,85 trong README ứng với cấu hình nào.
- Cần script `backend/scripts/eval_retrieval.py` chỉ chạy retrieval, không sinh câu trả lời; các chế độ `bm25`, `vector`, `hybrid`, `full` (hybrid + rerank + multi-query theo cấu hình).

## Phạm vi

- Bao gồm: `backend/scripts/eval_retrieval.py`, `backend/tests/test_eval_retrieval.py`, thư mục báo cáo `documents/rag-eval/`, trang task này.
- Ngoài phạm vi: đổi cấu hình `.env`/`.env.example`, sửa mã retrieval của app, sinh thêm dữ liệu đánh giá (việc của RAG-02), chạy Ragas.
- Ràng buộc:
  - Chỉ số hit@1/4/10 và MRR; "trúng" xác định bằng `expected_terms` so khớp sau chuẩn hóa NFKC + casefold + bỏ thẻ HTML, không phụ thuộc chunk ID.
  - Cache embedding câu hỏi ra file (khóa = model + text) để chạy lại không tốn API.
  - Mỗi báo cáo JSON ghi snapshot cấu hình RAG, model embedding, fingerprint kho tài liệu (hash các `content_hash` + số chunk), git commit, thời điểm chạy.
  - Có `--compare a.json b.json` in bảng chênh lệch.
  - Unit test phần chấm điểm chạy được khi không có mạng và không có `OPENAI_API_KEY`.

## Tiêu chí nghiệm thu

- [x] AC-01: `python -m scripts.eval_retrieval --mode hybrid` trên bộ 100 câu (`tests/fixtures/ptit_ragas_100.json`) chạy xong dưới 60 giây khi đã có cache embedding. — 4.5s.
- [x] AC-02: Hai lần chạy liên tiếp với cùng cấu hình cho kết quả giống hệt nhau. — metrics bằng tuyệt đối, 0/100 câu khác.
- [x] AC-03: Báo cáo JSON chứa đủ: cấu hình, model embedding, fingerprint kho, commit, chỉ số tổng và theo từng nhóm (tài liệu nguồn, loại câu hỏi, có dấu/không dấu).
- [x] AC-04: Có baseline cho cả 4 chế độ (`bm25`, `vector`, `hybrid`, `full`) trên index hiện tại, được commit kèm mô tả cấu hình (`documents/rag-eval/README.md`).
- [x] AC-05: Unit test cho hit@k, MRR, so khớp `expected_terms` chạy được khi không có mạng và không có `OPENAI_API_KEY`. — 13 passed; suite 247 passed / 1 skipped.
- [x] AC-06: `--compare` in được bảng chênh lệch giữa hai báo cáo.
- [x] AC-07 (mở rộng 2026-10-25 theo yêu cầu người dùng): thêm coverage@k (recall theo `expected_terms`) vào báo cáo, có unit test, chạy lại baseline 4 chế độ; hit/MRR không đổi so với bản trước. — cov@1/4/10: bm25 0.637/0.797/0.866, vector 0.530/0.749/0.826, hybrid 0.593/0.799/0.858, full 0.568/0.793/0.858.

## Tài liệu và phụ thuộc

- Không phụ thuộc task nào; làm đầu tiên. RAG-02 (bổ sung dữ liệu đánh giá) sẽ dùng lại script này.
- Liên quan: `.agents/tasks/2026-10-21-tests-off-data-corpus/` (đã soát `ptit_ragas_100.json`).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt (baseline cập nhật 2026-10-25 kèm coverage@k, index 1 tài liệu / 1269 chunk, fingerprint `ccf48780bbcc813d…`, commit code `2acff9660a83`):

  | mode | hit@1 | hit@4 | hit@10 | MRR | cov@1 | cov@4 | cov@10 |
  |---|---:|---:|---:|---:|---:|---:|---:|
  | bm25 | 0.690 | 0.830 | 0.900 | 0.755 | 0.637 | 0.797 | 0.866 |
  | vector | 0.590 | 0.800 | 0.870 | 0.688 | 0.530 | 0.749 | 0.826 |
  | hybrid | 0.650 | 0.840 | 0.900 | 0.739 | 0.593 | 0.799 | 0.858 |
  | full | 0.620 | 0.830 | 0.900 | 0.722 | 0.568 | 0.793 | 0.858 |

  Đọc số: BM25 dẫn đầu cả hit lẫn coverage, vector yếu nhất; hybrid với `HYBRID_VECTOR_WEIGHT=0.80` thua BM25 ở hit@1 — hạ trọng số vector là thí nghiệm đầu tiên. Khoảng cách hit@4 0.84 vs cov@4 0.80 (hybrid) cho thấy câu trúng vẫn thường thiếu một phần dữ kiện trong top-4. Chi tiết + cách reproduce: `documents/rag-eval/README.md`.
- Hoàn tất: script + test (16 unit test thuần; hit/MRR/rank từng câu giữ nguyên tuyệt đối so với bản 2026-10-24 — không hồi quy), 4 báo cáo baseline schema v2 + README; AC-01…AC-07 có bằng chứng trong `verification.md`; `review.md` self_review kết luận `approved` (R-03/R-04 low, trì hoãn có theo dõi).
- Blocker: không có.
- Bước tiếp theo: RAG-02 bổ sung câu không dấu + metadata `question_type`/`source` vào dataset — script tự nhóm, không cần đổi mã; sau đó thử hạ `HYBRID_VECTOR_WEIGHT` và bật multi-query/rerank rồi `--compare` với baseline này.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-24T23:54:57+07:00` — `zcode-agent`: tạo task từ yêu cầu người dùng; mode `full` tái dựng đúng pipeline `RagChain.retrieve_context` nhưng bỏ guardrail scope (không phải một phần của retrieval) và bỏ lọc `strong_context` (chỉ dùng để chốt câu trả lời); giữ lọc prompt-injection trên context.
- `2026-10-25T00:07:00+07:00` — `zcode-agent`: mọi AC đạt có bằng chứng; review self_review `approved`; task `done`.
- `2026-10-25T00:15:00+07:00` — `zcode-agent`: theo yêu cầu người dùng, mở rộng thêm AC-07 — coverage@k (recall theo term) vì hit@k chỉ cần một `expected_terms` là trúng trong khi 69/100 câu cần nhiều dữ kiện; precision không thêm vì thiếu nhãn liên quan từng chunk (chi tiết xem assessment trong implementation.md). Task quay lại `in_progress` rồi hoàn tất với baseline schema v2.

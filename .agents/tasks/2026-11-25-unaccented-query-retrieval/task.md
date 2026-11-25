# Task: Truy xuất và confidence gate cho câu hỏi không dấu không phụ thuộc LLM

- ID: `2026-11-25-unaccented-query-retrieval`
- Trạng thái: `in_progress`
- Coordinator: `agent-backend`
- Người yêu cầu: user
- Tạo lúc: `2026-11-25T21:08:20+07:00`
- Cập nhật lúc: `2026-11-25T21:30:00+07:00`

## Yêu cầu và kết quả mong muốn

Phát hiện N1: câu hỏi không dấu rất dễ bị từ chối nhầm.

- BM25 chỉ `casefold`, không bỏ dấu (`backend/app/retrieval/bm25.py` `_tokenize`), nên `hoc phi` không khớp `học phí`.
- Gate luôn bắt buộc `bm25_norm ≥ 0.25` (`backend/app/generation/confidence.py` `assess_context`).
- `QUERY_CORRECTION_ENABLED` mặc định tắt. Khi bật mà LLM lỗi, hết budget hoặc chưa cấu hình, câu gốc đi thẳng vào gate và trượt.
- Bộ RAGAS 100 câu (`ptit_ragas_100.json`) đều có dấu.

Số đo đã có (task `2026-11-21-llm-query-correction`, `documents/rag-eval/query-correction/`, đo 2026-11-21) cho thấy lỗi này **đã được đo** bằng `eval_confidence --perturb strip_all` nhưng chỉ ở chế độ tắt/bật LLM, chưa có cách sửa không cần LLM:

| `ptit_rag_300`, cờ tắt | Có dấu | Bỏ dấu |
|---|---|---|
| Qua gate | 284 | **0** |
| hit@4 | 249 | **40** |
| `vector ≥ 0.37` | 300 | 285 (median cosine 0.608 → 0.442) |
| `bm25_norm ≥ 0.25` | 284 | **0** (169/300 không có điểm BM25 trong top-4) |
| `strip_partial` (bỏ dấu một phần, n=104) qua gate | — | 1 |

Tức tín hiệu vector vẫn đạt, gate chết hoàn toàn vì BM25; thứ hạng (hit@4) cũng sụp vì RRF mất nhánh keyword và embedding câu không dấu kém hơn. Bật LLM sửa câu khôi phục được (281/300 qua gate, 245 hit@4) nhưng tốn một lượt gọi LLM mỗi câu, có đuôi trễ dài (p95 ≈ 12 s, HTTP 429) và mọi lỗi LLM đều rơi về hành vi trên.

Kết quả cần có: câu không dấu (toàn phần hoặc một phần) được truy xuất và qua gate gần mức câu có dấu **khi cờ sửa câu tắt hoặc LLM lỗi**, không làm thay đổi kết quả câu có dấu và không mở gate cho câu không có đáp án.

## Phạm vi

- Bao gồm: tokenizer/chỉ mục BM25 bỏ dấu (`backend/app/retrieval/`), tín hiệu và ngưỡng gate cho BM25 bỏ dấu (`backend/app/generation/confidence.py`, `backend/app/core/config.py`), khôi phục dấu tất định từ corpus làm fallback cho LLM (điều kiện, xem `plan.md` S-04), script/fixture đo (`backend/scripts/`, `documents/rag-eval/unaccented-query/`), test backend.
- Ngoài phạm vi: thay đổi prompt/validator của LLM sửa câu; đổi mặc định `QUERY_CORRECTION_ENABLED`; guardrail đầu vào (đã xử lý câu không dấu ở task `2026-11-18-guardrail-unaccented-scope`); UI ngoài việc hiển thị trường debug mới nếu có; re-embed hay đổi embedding model.
- Ràng buộc: câu có dấu giữ nguyên thứ hạng BM25, điểm `bm25_norm` và quyết định gate (so với baseline cùng commit nền). Không thêm dependency nặng (không model khôi phục dấu); chỉ dùng corpus đã index. Không dùng ngưỡng chưa đo: mọi ngưỡng mới phải ghi số đo trong `documents/rag-eval/unaccented-query/`.

## Tiêu chí nghiệm thu

Các số đo dưới đây chạy với `QUERY_CORRECTION_ENABLED=false` và cấu hình giống `documents/rag-eval/query-correction/README.md` (rewrite/multi-query LLM tắt, reranker tắt, top_k 4), trừ khi ghi khác.

- [ ] AC-01: Baseline trên commit nền được ghi lại cho `ptit_rag_300`, `ptit_faq`, `ptit_no_answer_56` với `--perturb none|strip_all|strip_partial|typo` (thêm chế độ `strip_partial` riêng vào `scripts/typo_variants.py`).
- [ ] AC-02: Không hồi quy câu có dấu: `--perturb none` cho cùng số câu qua gate và hit@4 như baseline trên `ptit_rag_300`/`ptit_faq`; số câu `ptit_no_answer_56` qua gate không tăng ở cả ba nhóm.
- [ ] AC-03: Câu bỏ dấu toàn bộ: `ptit_rag_300` qua gate ≥ 255/300 và hit@4 ≥ 224/300 (cùng mục tiêu tham khảo của task query-correction); `ptit_faq` qua gate ≥ 18/20.
- [ ] AC-04: Không mở gate cho câu không đáp án bỏ dấu: `ptit_no_answer_56 --perturb strip_all` từ chối `out_of_domain` 14/14; số câu `in_domain_missing` + `near_miss` qua gate ≤ con số của bản có dấu ở baseline AC-01.
- [ ] AC-05: Câu bỏ dấu một phần: `ptit_rag_300 --perturb strip_partial` qua gate ≥ 255/300; bộ `typo` không thấp hơn baseline ở mọi loại lỗi.
- [ ] AC-06: Fallback khi LLM hỏng: với `QUERY_CORRECTION_ENABLED=true` và LLM giả lập lỗi/hết budget, câu không dấu vẫn qua gate như AC-03 (test tự động trên `RAGChain` với provider giả, không cần endpoint thật).
- [ ] AC-07: `retrieval_debug` cho biết chỉ mục BM25 đã dùng và tín hiệu BM25 bỏ dấu (nếu có), đủ để đọc lý do qua/trượt gate; ngưỡng mới có thể đặt qua env và runtime config như `min_bm25_norm_score`.
- [ ] AC-08: Toàn bộ test backend (`pytest`, cần Postgres) và test mới cho tokenizer bỏ dấu, chọn chỉ mục, gate, fallback đều đạt.

## Tài liệu và phụ thuộc

- `documents/rag-eval/query-correction/README.md` — số đo bỏ dấu/lỗi gõ khi tắt/bật LLM.
- `documents/rag-eval/rag-18/` — hiệu chỉnh ngưỡng gate hiện tại.
- `.agents/tasks/2026-11-21-llm-query-correction/`, `.agents/tasks/2026-11-18-guardrail-unaccented-scope/`, `.agents/tasks/2026-11-08-rag18-confidence-gate/`.
- `backend/app/guardrails/normalization.py` (`strip_accents`, `has_accents`) — tái sử dụng, không viết lại.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01 xong trên nhánh `feat/unaccented-query-retrieval` (tách từ `dev` tại `b8c2ff3`): thêm chế độ đo `strip_partial`, số đo nền ở `documents/rag-eval/unaccented-query/`. Corpus hiện tại 993 chunk, khác bảng số ở mục đầu (1017 chunk); dùng số trong README mới làm mốc. Chưa sửa mã ứng dụng.
- Blocker: không có.
- Bước tiếp theo: `agent-backend` làm S-03. S-02 xong: BM25 riêng với câu bỏ dấu hit@4 46 → 240, nhưng hybrid chỉ 64 → 93 do nhánh vector; S-03 phải xử lý trọng số vector cho câu bỏ dấu.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-25T21:30:00+07:00 — agent-backend: user duyệt kế hoạch; tạo nhánh, chuyển `in_progress`. Baseline mới: bỏ dấu 0/300 qua gate, hit@4 50; bỏ dấu một phần 10/300, hit@4 173; câu không đáp án trong miền có dấu qua gate 20 (mốc AC-04).
- 2026-11-25T21:08:20+07:00 — agent-backend: tạo task từ phát hiện N1. Ghi nhận lỗi đã có số đo ở task query-correction (không phải "chưa từng đo"); phần chưa có là cách sửa không phụ thuộc LLM và bộ đo `strip_partial` riêng.

# Task: RAG-18 — Hiệu chỉnh confidence gate để từ chối khi context yếu

- ID: `2026-11-08-rag18-confidence-gate`
- Trạng thái: `in_review`
- Coordinator: `agent-claude`
- Người yêu cầu: `user` (thẻ Notion [RAG-18](https://app.notion.com/p/40f334d296eb81f4838cf5ab79d4fbec), ưu tiên P0, nguồn: rà soát toàn hệ thống 2026-11-05)
- Tạo lúc: `2026-11-08T00:15:00+07:00`
- Cập nhật lúc: `2026-11-08T09:08:55+07:00`

## Yêu cầu và kết quả mong muốn

**Hiện trạng.** `has_strong_context` (`backend/app/generation/confidence.py`) cho qua nếu **một** chunk bất kỳ vượt **một trong hai** ngưỡng: cosine `vector_score ≥ 0.30` hoặc BM25 thô `bm25_score ≥ 2.0` (`RETRIEVAL_MIN_VECTOR_SCORE`, `RETRIEVAL_MIN_BM25_SCORE`). Kết quả gate quyết định ở `backend/app/api/routes.py:1434-1450`: `strong_context=False` thì trả "Chưa tìm thấy thông tin này trong tài liệu." mà không gọi LLM.

- Với `text-embedding-3-small`, phần lớn đoạn văn tiếng Việt đã có cosine > 0.30 so với câu hỏi, nên nhánh vector gần như luôn đạt.
- BM25 thô (`rank_bm25.BM25Okapi`) phụ thuộc kích thước kho và độ dài query, nên ngưỡng 2.0 thay đổi ý nghĩa khi thêm tài liệu.
- Gate không dùng `rerank_score`. Lưu ý: reranker mặc định `heuristic` chuẩn hóa min-max **trong danh sách ứng viên** (`backend/app/retrieval/reranker.py:_normalize`), nên điểm này là tương đối và top-1 luôn cao; chỉ `cross-encoder` cho điểm tuyệt đối.
- Bộ đánh giá hiện có (`ptit_ragas_100.json`, `ptit_rag_300.json`) không có câu "không có đáp án", nên chưa từng đo tỉ lệ từ chối đúng.

Hệ quả: LLM vẫn được gọi với context yếu, tăng nguy cơ bịa hoặc trả lời lạc đề thay vì từ chối.

**Kết quả cần có.** Gate mới dựa trên tín hiệu có thang đo ổn định (cosine theo từng embedding model, BM25 chuẩn hóa, tùy chọn `rerank_score` khi provider cho điểm tuyệt đối), với ngưỡng được chọn từ phân bố điểm đo thực tế trên tập có đáp án và tập không có đáp án. Có báo cáo đo, unit test và cấu hình mẫu cập nhật.

## Phạm vi

- Bao gồm:
  - Tập ~50 câu không có đáp án/ngoài kho mới (`backend/tests/fixtures/`), có test lint.
  - Tín hiệu BM25 chuẩn hóa trong pipeline retrieval (`backend/app/retrieval/`).
  - Logic gate mới trong `backend/app/generation/confidence.py` và lời gọi trong `rag_chain.py`; đưa các tín hiệu gate vào `retrieval_debug`.
  - Cấu hình ngưỡng (`backend/app/core/config.py`, `config_store.py`, `backend/app/api/schemas.py`, `.env.example`), ngưỡng vector ghi theo embedding model.
  - Script đo phân bố điểm và quét ngưỡng (`backend/scripts/`), báo cáo trong `documents/rag-eval/rag-18/` và mục mới trong `documents/rag-eval/README.md`.
- Ngoài phạm vi:
  - Scope guardrail theo từ khóa (RAG-19), mở rộng toàn diện bộ đánh giá/CI (RAG-25); chỉ phối hợp schema với RAG-25.
  - Thay đổi chunking, ingest, trọng số hybrid/reranker, prompt sinh câu trả lời.
  - Giao diện admin `frontend/src/ConfigView.jsx`: không sửa trong task này. API cấu hình phải giữ tương thích để UI hiện tại không vỡ; thêm trường mới vào UI là việc tiếp theo nếu cần.
- Ràng buộc:
  - Đo không cần LLM: dùng query rewrite/multi-query theo luật như `eval_retrieval --mode full`; embedding câu hỏi dùng cache `backend/storage/eval/embedding_cache.json`.
  - Cosine giữa các embedding model không so sánh được: ngưỡng vector phải gắn với tên model; model chưa hiệu chỉnh phải có hành vi dự phòng rõ ràng (log cảnh báo, không âm thầm dùng ngưỡng của model khác như thể đã hiệu chỉnh).
  - Không đổi âm thầm ý nghĩa của `retrieval_min_bm25_score`: giá trị 2.0 (thang thô) đã có thể được lưu trong runtime config (`config_store.py`); nếu áp lên thang chuẩn hóa [0, 1] sẽ từ chối mọi câu.
  - Nhánh `feat/rag18-confidence-gate` tách từ `dev` đã cập nhật; commit message tiếng Anh. Working tree `dev` hiện báo nhiều file `M` — kiểm tra là chỉ stat/CRLF (`git diff HEAD --name-only` rỗng) trước khi tạo nhánh; nếu có thay đổi nội dung thật thì hỏi người dùng.

## Tiêu chí nghiệm thu

- [x] AC-01: Có fixture ≥ 50 câu không có đáp án (`answerable: false`), mỗi câu có `category` và `why_unanswerable`; được kiểm là không có đáp án trong kho đang index (ghi cách kiểm). Ít nhất 70% số câu lọt qua scope guardrail hiện tại (`check_scope`) để thực sự kiểm được gate. Có test lint schema/trùng lặp.
- [x] AC-02: Báo cáo phân bố điểm top-1 (vector, BM25 thô, BM25 chuẩn hóa, rerank) cho câu có đáp án và câu không có đáp án, bảng quét ngưỡng và ngưỡng được chọn kèm lý do; lưu trong `documents/rag-eval/rag-18/` (JSON + mục README), ghi embedding model, reranker provider, fingerprint kho, dataset sha256, git commit.
- [ ] AC-03 (đạt với reranker cross-encoder 0.824 gate-only / 0.839 e2e; chưa đạt với heuristic mặc định 0.373 — chờ người dùng): Trên tập không có đáp án: tỉ lệ từ chối ≥ 80% (báo cáo cả số gate-only và end-to-end gồm scope guardrail; tiêu chí áp cho end-to-end, gate-only phải ≥ 80% trên các câu lọt scope guardrail).
- [x] AC-04 (đo gate-only theo xác nhận của người dùng 2026-11-08: 4.0% với cross-encoder, ≤ 5% ở cả 3 cấu hình; e2e 17.3% do scope guardrail, theo dõi ở RAG-19): Trên golden set `ptit_rag_300.json`: từ chối nhầm ≤ 5% trên toàn bộ câu; báo cáo thêm tỉ lệ trên `ptit_ragas_100.json` và tỉ lệ trên nhóm câu retrieval trúng hit@4.
- [x] AC-05: Unit test cho gate mới (đạt/không đạt theo từng tín hiệu, thiếu tín hiệu, context rỗng, model chưa hiệu chỉnh) và cho BM25 chuẩn hóa (nằm trong [0, 1], không phụ thuộc kích thước kho theo cách của điểm thô); `python -m pytest` toàn bộ backend xanh.
- [x] AC-06: `.env.example` và cấu hình cập nhật ngưỡng mới; ngưỡng vector ghi theo embedding model; API `/config` giữ tương thích ngược (các test `test_config_api.py`, `test_config_persistence.py` và test frontend liên quan vẫn xanh) và giá trị BM25 thô đã lưu không làm gate từ chối mọi câu.

## Tài liệu và phụ thuộc

- Notion: [RAG-18](https://app.notion.com/p/40f334d296eb81f4838cf5ab79d4fbec); phối hợp [RAG-25](https://app.notion.com/p/40f334d296eb8142a42af4f2117ce91d) (schema câu không có đáp án), liên quan RAG-19 (scope guardrail).
- Mã: `backend/app/generation/confidence.py`, `backend/app/generation/rag_chain.py:234-262`, `backend/app/api/routes.py:1434-1450`, `backend/app/retrieval/{bm25,hybrid,multi_query,parent_child,reranker}.py`, `backend/app/core/config.py:145-146, 530-531, 658-661`, `backend/app/core/config_store.py:76-77`, `backend/app/api/schemas.py:313-316, 388-391`.
- Đánh giá: `documents/rag-eval/README.md`, `backend/scripts/eval_retrieval.py` (chế độ `full`), `backend/tests/fixtures/ptit_rag_300.json`, `backend/tests/fixtures/ptit_ragas_100.json`, task `2026-11-07-rag-testset-300`.
- Test hiện có: `backend/tests/test_retrieval_confidence.py`, `test_rag_chain.py`, `test_config_api.py`, `test_config_persistence.py`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01…S-06 xong trên nhánh `feat/rag18-confidence-gate` (`bcd6cd0..704f08b`, chưa push). Gate mới: AND trên `bm25_norm ≥ 0.25`, cosine ≥ 0.37 (`text-embedding-3-small`), cross-encoder ≥ −1.65 (chỉ khi provider `cross-encoder`). Báo cáo `documents/rag-eval/rag-18/`. Self-review `approved`.
- Blocker: không có blocker kỹ thuật. AC-04 đã được người dùng xác nhận tính gate-only; còn chờ quyết định về reranker mặc định cho AC-03 (`MSG-agent-claude-002`).
- Bước tiếp theo: PR vào `dev` đã mở theo yêu cầu người dùng; chờ quyết định AC-03 và merge, sau đó cập nhật thẻ Notion và chuyển `done`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-08T00:15:00+07:00 — agent-claude: tạo task từ thẻ Notion RAG-18, trạng thái `ready`. Bổ sung so với thẻ: (1) yêu cầu ≥ 70% câu không có đáp án lọt scope guardrail, để tỉ lệ từ chối không bị scope guardrail "làm hộ"; (2) giữ tương thích ngược `min_bm25_score` vì runtime config có thể đã lưu giá trị thang thô; (3) chỉ dùng `rerank_score` khi provider cho điểm tuyệt đối; (4) UI admin để ngoài phạm vi.
- 2026-11-08T00:49:19+07:00 — agent-claude: chuyển `in_review`. Quyết định phạm vi: (1) đo AC-04 theo gate-only (gate áp lên mọi câu), báo cáo e2e bên cạnh, vì scope guardrail (RAG-19, ngoài phạm vi) đã chặn 14.7% câu `ptit_rag_300` trước gate; (2) theo plan S-04, heuristic không đạt AC-03 nên đã đo và hiệu chỉnh cross-encoder; không đổi `RERANKER_PROVIDER` mặc định (thay đổi reranker nằm ngoài phạm vi) — hỏi người dùng (`MSG-agent-claude-002`); (3) fixture đặt tên `ptit_no_answer_56.json` (56 câu) thay cho `ptit_no_answer_50.json`; (4) sửa thêm fixture giả trong 3 file test chat/LLM ngoài danh sách S-05 vì hợp đồng gate mới cần `bm25_norm_score`.
- 2026-11-08T09:08:55+07:00 — user: xác nhận AC-04 tính gate-only (gate áp lên mọi câu); yêu cầu push và mở PR. AC-03 (reranker mặc định) chưa có quyết định.

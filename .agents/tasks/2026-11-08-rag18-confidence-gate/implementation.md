# Implementation: 2026-11-08-rag18-confidence-gate

## Tổng quan triển khai

- Nhánh `feat/rag18-confidence-gate` tách từ `dev` tại `bcd6cd0` (đã `git fetch`, `dev` = `origin/dev`). Trước khi tạo nhánh: `git diff HEAD --name-only` rỗng — các file `M` trên `dev` chỉ là stat/CRLF, vẫn còn trong working tree và không được commit.
- Đã tích hợp đủ S-01…S-06 trên nhánh (chưa push, chưa mở PR):

| Commit | Nhiệm vụ |
|---|---|
| `9b37ee2` feat: add query-normalized bm25_norm_score to retrieval results | S-02 |
| `c4016a9` test: add 56-case unanswerable question set with lint checks | S-01 |
| `d324064` feat: add eval_confidence script to measure gate signals and sweep thresholds | S-03 |
| `4289a13` feat: gate LLM calls on calibrated bm25_norm, vector and cross-encoder thresholds | S-04 (xóa biến thể BM25 bị loại) + S-05 |
| `ab00217` docs: add RAG-18 confidence gate measurements and threshold report | S-06 |
| `704f08b` docs: clarify how corpus size still affects bm25_norm_score | sửa sau self-review (R-01) |

- Chờ: quyết định của người dùng về reranker mặc định (xem `MSG-agent-claude-002`), push + PR vào `dev`, cập nhật thẻ Notion RAG-18.

## Nhật ký theo nhiệm vụ

### S-01 — agent-claude

- Cập nhật lúc: `2026-11-08T00:49:19+07:00`.
- Đã làm: `backend/tests/fixtures/ptit_no_answer_56.json` — 56 câu (`in_domain_missing` 22, `near_miss` 20, `out_of_domain` 14), mỗi câu có `answerable: false`, `category`, `why_unanswerable`, `probe_terms`. Tên file theo số câu (giống `ptit_rag_300.json`) thay cho `ptit_no_answer_50.json` trong plan. 51/56 câu (91%) lọt `check_scope`; 5 câu bị chặn đều là `out_of_domain`.
- Cách kiểm không có đáp án:
  1. `probe_terms` (cụm từ khóa mà câu trả lời buộc phải chứa) không xuất hiện trong bản converted `storage/converted/74650b….md` (cùng nguồn task `2026-11-07-rag-testset-300`) — test `test_probe_terms_are_absent_from_handbook`.
  2. Index đang chạy là bản LlamaParse agentic của PDF (`documents.content_hash` `eab94696…`, 1010 chunk), khác bản converted trên. Đã quét `probe_terms` trên toàn bộ `chunks.text` trong DB: chỉ một khớp, `wifi` trong chú thích ảnh "icon: wifi signal" → đổi probe của `noans_002` thành `mật khẩu wifi` / `mạng wifi` / `wi-fi`.
  3. Đọc top-3 context (pipeline `full`, cấu hình `.env` local) của 42 câu trong miền: không context nào chứa câu trả lời. Các câu dễ gây nhầm nhất ghi trong `why_unanswerable` (ví dụ `noans_011`, `noans_027` kéo về Điều 10 Nghị định học phí — chỉ có mức trần quốc gia, không có học phí PTIT). Top-3 context của mọi câu được lưu trong `documents/rag-eval/rag-18/*.json` (`cases[].retrieved`).
- Thay một câu nháp ("có khám sức khỏe định kỳ không") vì Sổ tay có nhắc khám sức khỏe định kỳ → thay bằng câu hỏi nơi khám đầu khóa.
- File: `backend/tests/fixtures/ptit_no_answer_56.json`, `backend/tests/test_no_answer_set.py` (schema, id, category, không trùng câu với `ptit_rag_300`/`ptit_ragas_100`, ≥ 70% lọt scope và mọi câu trong miền lọt scope, probe vắng mặt trong Sổ tay). Commit `c4016a9`.
- Kiểm tra: `pytest tests/test_no_answer_set.py -q` → `5 passed`.

### S-02 — agent-claude

- Cập nhật lúc: `2026-11-08T00:49:19+07:00`.
- Đã làm: `BM25Search.search` gán `bm25_norm_score = raw / upper_bound(query)` kẹp [0, 1]; `hybrid.py` chép trường từ nhánh keyword (kể cả khi chunk vào trước từ nhánh vector); `multi_query.py`, `parent_child.py` gộp bằng max; `bm25_score` thô giữ nguyên.
- Khác hợp đồng trong `plan.md`: cận trên cộng **theo từng token kể cả token lặp** (không phải term duy nhất), vì `BM25Okapi.get_scores` cũng cộng theo token lặp — cộng theo term duy nhất thì điểm thô có thể vượt cận. idf của term chưa thấy dùng cùng sàn epsilon như `BM25Okapi` để kho rất nhỏ không ra idf âm.
- Biến thể term ngoài từ vựng: cài tạm cờ `_UNSEEN_TERM_MODE` (`df1` / `skip`), S-04 chọn `df1`, cờ đã xóa trong `4289a13`.
- File: `backend/app/retrieval/{bm25,hybrid,multi_query,parent_child}.py`, `backend/tests/test_bm25_normalized.py` (mới), `backend/tests/test_hybrid_retrieval.py`, `backend/tests/test_multi_query.py`. Commit `9b37ee2`, docstring sửa ở `704f08b`.
- Kiểm tra: `pytest tests/test_bm25_normalized.py tests/test_hybrid_retrieval.py tests/test_multi_query.py -q` → `12 passed`. Thứ hạng không đổi: xem V-05.

### S-03 — agent-claude

- Cập nhật lúc: `2026-11-08T00:49:19+07:00`.
- Đã làm: `backend/scripts/eval_confidence.py` (import `build_retrieval_fn("full")`, `CachedEmbeddingModel`, `snapshot_*`, `git_info`, `first_hit_rank`, `warm_cache_texts`, `dataset_sha256` từ `eval_retrieval.py`; **không sửa** `eval_retrieval.py`). `--set key=value` ghi đè settings trong phiên đo; `--from-report` tính lại tóm tắt/sweep từ JSON có sẵn; `--sweep` quét `or_raw`, `vector`, `bm25_raw`, `bm25_norm`, `and`, `or_norm`, `weighted`, `rerank`, `rerank_and_norm` (luật `rerank*` chỉ quét khi báo cáo dùng cross-encoder), ràng buộc từ chối nhầm `ptit_rag_300` ≤ 5%, kèm biên Pareto và ±10% quanh điểm tốt nhất. Ghi cả quyết định gate cũ và gate đang cài cho từng câu.
- Định nghĩa số đo: gate-only = gate áp lên mọi câu (bỏ qua scope); e2e = scope chặn hoặc gate từ chối. Với câu không có đáp án, gate-only tính trên các câu lọt scope.
- File: `backend/scripts/eval_confidence.py`, `backend/tests/test_eval_confidence.py`. Commit `d324064` (+ chỉnh ở `4289a13`, `ab00217`).
- Kiểm tra: `pytest tests/test_eval_confidence.py -q` → `12 passed`.
- Hướng dẫn chạy: xem mục RAG-18 trong `documents/rag-eval/README.md`.

### S-04 — agent-claude

- Cập nhật lúc: `2026-11-08T00:49:19+07:00`.
- Đã làm: đo 4 biến thể (cấu hình `.env` local / núm retrieval `.env.example` × biến thể term ngoài kho `df1` / `skip`), rồi cross-encoder. Báo cáo nháp nằm trong thư mục tạm của phiên; số cuối ở S-06. Quyết định: `MSG-agent-claude-001`.
- Không sửa mã ngoài việc xóa biến thể BM25 bị loại.

### S-05 — agent-claude

- Cập nhật lúc: `2026-11-08T00:49:19+07:00`.
- Đã làm:
  - `confidence.py`: `GateThresholds`, `ConfidenceDecision`, `thresholds_from_settings()`, `assess_context()`; bảng `VECTOR_THRESHOLDS` (`text-embedding-3-small`: 0.37) và `RERANK_THRESHOLDS` (`mmarco-mMiniLMv2-L12-H384-v1`: −1.65). Gate đạt khi mọi tín hiệu đang dùng vượt ngưỡng; thiếu tín hiệu = không đạt. `has_strong_context` đã xóa (không còn import nào).
  - Model embedding / reranker chưa hiệu chỉnh: bỏ tín hiệu đó, log cảnh báo một lần, `reason=passed_uncalibrated_model` khi đạt và `thresholds.vector_source=uncalibrated` trong debug.
  - `rag_chain.py`: giữ `strong_context`; thêm `retrieval_debug["confidence"] = {reason, signals, thresholds}`; thêm `bm25_norm_score` vào `DEBUG_CHUNK_FIELDS`. `routes.py` không sửa.
  - Cấu hình: `retrieval_min_vector_score: float | None` (mặc định `None` = bảng theo model); `retrieval_min_bm25_norm_score` (0.25); `retrieval_min_rerank_score: float | None`; `retrieval_min_bm25_score` giữ nguyên nhưng deprecated, gate không dùng. Env để trống → `None` (validator). Hai trường mới vào `PERSISTED_FIELDS`.
  - Tương thích runtime config / UI: giá trị 0.30 (mặc định cũ, chưa từng hiệu chỉnh) được coi là chưa đặt — ở cả env, DB đã lưu và API. `GET /config` trả `min_vector_score` = ngưỡng hiệu lực (`None` nếu chưa hiệu chỉnh) + `min_bm25_norm_score`, `min_rerank_score`, `vector_threshold_source`. `PUT /config` với `min_vector_score` trùng ngưỡng hiệu lực hoặc 0.30 thì không tạo ghi đè (UI hiện tại gửi lại mọi ngưỡng mỗi lần lưu). Muốn bỏ ghi đè vector đã đặt: `POST /config/reset` hoặc sửa env.
  - `.env.example`: thêm `RETRIEVAL_MIN_BM25_NORM_SCORE=0.25`, để trống `RETRIEVAL_MIN_VECTOR_SCORE`/`RETRIEVAL_MIN_RERANK_SCORE` kèm giải thích, đánh dấu `RETRIEVAL_MIN_BM25_SCORE` deprecated.
- Ngoài danh sách file của plan (coordinator ghi nhận): `tests/test_llm_budget.py`, `tests/test_llm_provider_cache.py`, `tests/test_chat_error_privacy.py` — mỗi file thêm `bm25_norm_score` vào một context giả "mạnh"; context chỉ có BM25 thô giờ bị gate từ chối, đúng hành vi mới.
- File: `backend/app/generation/{confidence,rag_chain}.py`, `backend/app/core/{config,config_store}.py`, `backend/app/api/schemas.py`, `.env.example`, `backend/tests/test_{retrieval_confidence,rag_chain,config_api,config_persistence}.py` + 3 file test nêu trên. Commit `4289a13`.
- Kiểm tra: toàn bộ backend pytest xanh (V-06).

### S-06 — agent-claude

- Cập nhật lúc: `2026-11-08T00:49:19+07:00`.
- Đã làm: chạy lại `eval_confidence --sweep` với gate đã cài cho 3 cấu hình, lưu `documents/rag-eval/rag-18/{local_env,example_heuristic,example_cross_encoder}.{json,txt}`; so `eval_retrieval --mode full/hybrid` giữa `bcd6cd0` (worktree tạm, đã xóa) và nhánh; thêm mục "RAG-18" vào `documents/rag-eval/README.md` (đưa file từ CRLF trong working tree về LF như index). Commit `ab00217`.

## Trao đổi giữa agents

### MSG-agent-claude-001

- Lúc: `2026-11-08T00:49:19+07:00`.
- Từ: `agent-claude`; đến: `coordinator` (cùng agent).
- Nhiệm vụ: `S-04`.
- Loại: `decision`.
- Nội dung:
  - Biến thể BM25: `df1` (term ngoài kho tính idf của df = 1). `skip` kém hơn ở mọi luật (chỉ `bm25_norm`: 0.471 so với 0.588 từ chối đúng tại cùng ngân sách).
  - Tín hiệu heuristic (cosine, BM25 thô/chuẩn hóa, mọi luật kết hợp) không vượt ~0.69 từ chối đúng gate-only khi giữ từ chối nhầm `ptit_rag_300` ≤ 5% → theo plan đo thêm cross-encoder.
  - Luật chọn: AND trên mọi tín hiệu đã hiệu chỉnh — `bm25_norm ≥ 0.25` (luôn dùng), cosine ≥ 0.37 (`text-embedding-3-small`, chỉ là sàn an toàn), cross-encoder ≥ −1.65 (chỉ khi provider `cross-encoder`).
  - Lý do chọn ngưỡng và phương án bị loại (tổng có trọng số, OR, điểm tối ưu sát biên −1.55/0.26, sàn cosine cao hơn, ngưỡng `bm25_norm` riêng cho heuristic): ghi trong mục RAG-18 của `documents/rag-eval/README.md`.
- Hành động mong muốn: S-05 cài theo quyết định này (đã làm).

### MSG-agent-claude-002

- Lúc: `2026-11-08T00:49:19+07:00`.
- Từ: `agent-claude`; đến: `user`.
- Nhiệm vụ: `S-06` / `AC-03`, `AC-04`.
- Loại: `question`.
- Nội dung:
  1. AC-03 (≥ 80% từ chối đúng) chỉ đạt khi reranker là cross-encoder (gate-only 0.824, e2e 0.839). Với reranker `heuristic` của `.env.example` gate chỉ từ chối 0.373 (từ chối nhầm 1.3%); với `.env` local (reranker tắt, multi-query tắt) 0.588. Đổi mặc định `RERANKER_PROVIDER=cross-encoder` là thay đổi triển khai (model ~470 MB, ≈ +0.12 s/câu trên CPU) nằm ngoài phạm vi RAG-18 nên chưa làm.
  2. AC-04 được đo gate-only (gate áp lên mọi câu): 4.0% với cross-encoder. Scope guardrail hiện tại đã chặn 14.7% câu `ptit_rag_300` trước gate (RAG-19), nên e2e là 17.3% — không đạt 5% nếu hiểu AC-04 theo e2e, dù gate không phải nguyên nhân.
- Hành động mong muốn: người dùng chọn (a) đổi reranker mặc định sang cross-encoder trong task tiếp theo hay chấp nhận AC-03 có điều kiện; (b) xác nhận AC-04 tính gate-only.

## Bàn giao

### HANDOFF-agent-claude-001 — S-01…S-06

- Từ / đến: `agent-claude` / `user` (reviewer độc lập nếu có).
- Đã hoàn tất: S-01…S-06 như trên.
- File/branch/commit: nhánh `feat/rag18-confidence-gate`, `bcd6cd0..704f08b` (6 commit), chưa push.
- Kiểm chứng: `verification.md` V-01…V-06.
- Review: `review.md` — `self_review`, kết luận `approved` cho mã; R-02, R-03 hoãn lại chờ quyết định.
- Hạn chế / còn lại: AC-03 có điều kiện (cross-encoder); cách hiểu AC-04; push/PR; cập nhật Notion.
- Bước tiếp theo: người dùng trả lời `MSG-agent-claude-002`; sau đó push, mở PR vào `dev`, chuyển task `done`.
- Phản hồi nhận bàn giao: (chờ).

### MSG-user-001

- Lúc: `2026-11-08T09:08:55+07:00`.
- Từ: `user`; đến: `agent-claude`.
- Nhiệm vụ: `AC-04`.
- Loại: `reply`.
- Tham chiếu: `MSG-agent-claude-002`.
- Nội dung: "AC-04 gate-only is fine, push and open the PR". Câu hỏi về reranker mặc định (AC-03) chưa được trả lời.
- Hành động mong muốn: push nhánh, mở PR vào `dev` (đã làm).

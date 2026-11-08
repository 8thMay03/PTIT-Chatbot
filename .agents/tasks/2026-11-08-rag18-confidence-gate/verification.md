# Verification: 2026-11-08-rag18-confidence-gate

- Verifier: `agent-claude`.
- Trạng thái tổng: `passed` cho AC-01, AC-02, AC-05, AC-06; AC-03 `passed` có điều kiện (chỉ với reranker cross-encoder) — chờ quyết định reranker mặc định (`MSG-agent-claude-002`); AC-04 `passed` (gate-only, người dùng xác nhận).
- Bản được kiểm tra: nhánh `feat/rag18-confidence-gate`, commit `704f08b` (số đo ở commit `4289a13`; `704f08b` chỉ đổi docstring).
- Môi trường: Windows 11, Python 3.11 `backend/.venv`, Postgres local (1 tài liệu Sổ tay D26 — LlamaParse agentic, 1010 chunk, fingerprint `d33ac7329944…`), embedding OpenAI `text-embedding-3-small` qua cache `backend/storage/eval/embedding_cache.json`, `sentence-transformers` 5.6.0 cho cross-encoder; Node/Vitest cho frontend.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: agent-claude / `2026-11-08T00:49:19+07:00`.
- Loại: test tự động + kiểm tra thủ công.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest tests/test_no_answer_set.py -q`; quét `probe_terms` trên `chunks.text` của DB; đọc top-3 context của 42 câu trong miền (xem `implementation.md` S-01).
- Kỳ vọng: ≥ 50 câu `answerable: false` có `category`, `why_unanswerable`; ≥ 70% lọt `check_scope`; test lint schema/trùng lặp.
- Kết quả thực tế: 56 câu; 51/56 (91.1%) lọt scope (100% `in_domain_missing` và `near_miss`, 64.3% `out_of_domain`); `5 passed`; quét DB: 1 khớp ở chú thích ảnh → đã sửa probe; đọc top-3: không context nào chứa câu trả lời.
- Trạng thái: `passed`.
- Bằng chứng: `backend/tests/fixtures/ptit_no_answer_56.json`, `backend/tests/test_no_answer_set.py`, `summary.scope_pass` trong `documents/rag-eval/rag-18/*.json`.

### V-02 — AC-02

- Người thực hiện / thời gian: agent-claude / `2026-11-08T00:49:19+07:00`.
- Loại: review tài liệu + chạy script.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `python -m scripts.eval_confidence --sweep --output ../documents/rag-eval/rag-18/<cấu hình>.json` cho 3 cấu hình (lệnh đầy đủ trong README mục RAG-18).
- Kỳ vọng: phân bố top-1 (vector, BM25 thô, BM25 chuẩn hóa, rerank) cho câu có/không có đáp án, bảng quét, ngưỡng chọn + lý do; ghi embedding model, reranker, fingerprint kho, sha256 dataset, git commit.
- Kết quả thực tế: mỗi JSON có `embedding`, `reranker`, `corpus.fingerprint`, `datasets[].sha256`, `git`, `config`, `gate_thresholds`, `summary.distributions`, `summary.sweep` (best + Pareto + ±10%); `.txt` có percentile/histogram; README có bảng phân bố, bảng quét 3 cấu hình, ngưỡng chọn, lý do, phương án loại, giới hạn. `git.dirty=True` do các file stat/CRLF có sẵn trên `dev` (không có thay đổi nội dung).
- Trạng thái: `passed`.
- Bằng chứng: `documents/rag-eval/rag-18/`, `documents/rag-eval/README.md` mục "RAG-18".

### V-03 — AC-03

- Người thực hiện / thời gian: agent-claude / `2026-11-08T00:49:19+07:00`.
- Loại: đo tự động bằng gate đã cài (`cases[].gate` do `assess_context` sinh, không mô phỏng).
- Thư mục chạy: `backend`.
- Lệnh / thao tác: như V-02.
- Kỳ vọng: từ chối đúng ≥ 80% e2e; gate-only ≥ 80% trên câu lọt scope.
- Kết quả thực tế:

| Cấu hình | gate-only (51 câu) | e2e (56 câu) |
|---|---:|---:|
| `example_cross_encoder` | **0.824** | **0.839** |
| `local_env` (reranker tắt) | 0.588 | 0.625 |
| `example_heuristic` | 0.373 | 0.429 |
| gate cũ (mọi cấu hình) | 0.000 | 0.089 |

- Trạng thái: `passed` với reranker cross-encoder; `failed` với reranker heuristic / tắt (mặc định hiện tại của `.env.example` là heuristic).
- Bằng chứng: `summary.gate` trong ba JSON; `MSG-agent-claude-002`.

### V-04 — AC-04

- Người thực hiện / thời gian: agent-claude / `2026-11-08T00:49:19+07:00`.
- Loại: đo tự động bằng gate đã cài.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: như V-02.
- Kỳ vọng: từ chối nhầm ≤ 5% trên toàn bộ `ptit_rag_300`; báo cáo thêm `ptit_ragas_100` và nhóm hit@4.
- Kết quả thực tế (gate-only / e2e):

| Cấu hình | `rag_300` | `rag_300` hit@4 | `ragas_100` | `ragas_100` hit@4 |
|---|---:|---:|---:|---:|
| `example_cross_encoder` | **0.040** / 0.173 | 0.011 / 0.153 | 0.040 / 0.040 | 0.011 / 0.011 |
| `local_env` | **0.050** / 0.180 | 0.024 / 0.168 | 0.060 / 0.060 | 0.039 / 0.039 |
| `example_heuristic` | **0.013** / 0.157 | 0.000 / 0.160 | 0.020 / 0.020 | 0.000 / 0.000 |

- Trạng thái: `passed` (gate-only, người dùng xác nhận đây là cách đo AC-04 ngày 2026-11-08). E2E 0.173 do scope guardrail đã chặn 14.7% câu `ptit_rag_300` trước gate (gate cũ cũng e2e 0.147) — theo dõi ở RAG-19.
- Bằng chứng: `summary.gate.false_refusal` / `false_refusal_e2e`, `summary.scope_pass` trong JSON.

### V-05 — AC-05

- Người thực hiện / thời gian: agent-claude / `2026-11-08T00:49:19+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q -p no:cacheprovider`; so thứ hạng: `python -m scripts.eval_retrieval --mode full|hybrid --dataset tests/fixtures/ptit_rag_300.json` ở `bcd6cd0` (worktree tạm) và ở nhánh, so `cases[].retrieved` (chunk_id + score).
- Kỳ vọng: test gate (đạt/không đạt từng tín hiệu, thiếu tín hiệu, context rỗng, model chưa hiệu chỉnh) và BM25 chuẩn hóa ([0, 1], ổn định hơn điểm thô khi kho lớn lên); toàn bộ backend xanh; thứ hạng không đổi.
- Kết quả thực tế: `1272 passed, 24 skipped` (lần chạy cuối, sau `ab00217`; `704f08b` chỉ đổi docstring, `test_bm25_normalized.py` chạy lại `5 passed`). So thứ hạng: 0/300 câu khác top-10 ở cả `full` và `hybrid`; full hit@1/4/10/MRR = 0.617/0.823/0.887/0.709 cả hai bên.
- Trạng thái: `passed`.
- Bằng chứng: `tests/test_retrieval_confidence.py` (13 test), `tests/test_bm25_normalized.py` (5 test, gồm kho lớn gấp 8: điểm thô đổi > 30%, điểm chuẩn hóa đổi < 0.1).

### V-06 — AC-06

- Người thực hiện / thời gian: agent-claude / `2026-11-08T00:49:19+07:00`.
- Loại: test tự động + review cấu hình.
- Thư mục chạy: `backend`, `frontend`.
- Lệnh / thao tác: `pytest tests/test_config_api.py tests/test_config_persistence.py tests/test_retrieval_confidence.py -q`; `npx vitest run src/ConfigView.cache.test.jsx src/admin/AdminApp.test.jsx`.
- Kỳ vọng: `.env.example` + cấu hình có ngưỡng mới; ngưỡng vector theo model; `/config` tương thích ngược; BM25 thô đã lưu không làm gate từ chối mọi câu.
- Kết quả thực tế: backend xanh (gồm test mới: GET trả ngưỡng hiệu lực; lưu lại ngưỡng đang hiển thị / 0.30 cũ không tạo ghi đè; `min_bm25_norm_score` cập nhật + lưu DB + còn sau restart; `retrieval_min_bm25_score = 1000` không ảnh hưởng gate); frontend `7 passed` (2 file). Không sửa `ConfigView.jsx`.
- Trạng thái: `passed`.
- Bằng chứng: `.env.example`, `backend/app/core/config.py`, `backend/tests/test_config_api.py`, `backend/tests/test_config_persistence.py`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy pytest đầu sau S-05: 11 test thất bại (fixture giả chỉ có `bm25_score` thô, gate mới từ chối) → thêm `bm25_norm_score` vào fixture; chạy lại xanh.
- Chưa đo cross-encoder với cấu hình `.env` local (multi-query tắt); chưa đo trên kho nhiều tài liệu.
- Chưa chạy toàn bộ test frontend, chỉ hai file liên quan cấu hình.

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-02, AC-05, AC-06; AC-04 (gate-only); AC-03 (với cross-encoder).
- Tiêu chí chưa đạt/chưa xác minh: AC-03 với reranker mặc định heuristic; AC-04 theo e2e (do scope guardrail).
- Đề xuất: chờ người dùng quyết định theo `MSG-agent-claude-002` trước khi coordinator chuyển `done`.

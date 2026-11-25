# Implementation: 2026-11-25-unaccented-query-retrieval

## Tổng quan triển khai

Nhánh `feat/unaccented-query-retrieval` (tách từ `dev` tại `b8c2ff3`). S-01, S-02, S-03, S-05 xong; S-04 hủy (quyết định của user). Chờ review vòng cuối.

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

### S-03 — agent-backend

- Cập nhật lúc: `2026-11-25T22:02:09+07:00`.
- Đã làm:
  - `retrieval/bm25.py`: thay quy tắc chọn chỉ mục của S-02. Chỉ mục bỏ dấu dùng khi câu **gõ thiếu dấu**: có chữ không dấu không nằm trong từ vựng chỉ mục có dấu nhưng nằm trong từ vựng chỉ mục bỏ dấu (`_missing_accents`). Lý do: quy tắc cũ đổi chunk của 13 câu có dấu khớp yếu và sẽ đưa tín hiệu bỏ dấu tới câu có dấu (mở gate cho câu không đáp án có dấu); quy tắc mới giữ 375/376 câu có dấu y như baseline (câu còn lại: `la` trong "đô la").
  - `retrieval/retriever.py`: `_vector_weight`: BM25 xếp theo chỉ mục bỏ dấu thì RRF dùng `settings.hybrid_folded_vector_weight` (mặc định 0.3; để trống = `hybrid_vector_weight`).
  - `generation/confidence.py`: `GateThresholds.min_bm25_folded_norm_score` (mặc định 0.40, `None` = tắt); `signals.bm25_folded_norm`; `bm25_folded_norm ≥` ngưỡng thì bỏ qua kiểm tra `bm25_norm` và `vector`, rerank vẫn xét; `reason` giữ mã cũ.
  - `core/config.py`: `HYBRID_FOLDED_VECTOR_WEIGHT`, `RETRIEVAL_MIN_BM25_FOLDED_NORM_SCORE` (để trống = `None`); snapshot `guardrails.min_bm25_folded_norm_score`; áp dụng runtime config (kẹp [0, 1]). `config_store.py`: lưu `retrieval_min_bm25_folded_norm_score`. `api/schemas.py`: trường mới trong payload/cập nhật guardrails. `HYBRID_FOLDED_VECTOR_WEIGHT` chỉ qua env (không thêm runtime config/UI).
  - `scripts/eval_confidence.py`: schema v3, tín hiệu `bm25_folded_norm`, `cases[].bm25_index`, histogram, luật sweep `bm25_or_folded` khớp gate mới.
  - `.env.example`: hai biến mới.
  - Test: `test_retrieval_confidence.py` (+5: nhánh bỏ dấu không cần vector, dưới ngưỡng, tắt ngưỡng, vẫn xét rerank, ngưỡng từ settings), `test_config_api.py` (+1, GET có trường mới), `test_config_persistence.py` (+1), `test_bm25_folded.py` (đổi 2 test theo quy tắc mới, +2: câu có dấu khớp yếu giữ chỉ mục có dấu, chữ không dấu có sẵn trong kho không kích hoạt; +1 `_vector_weight`), `test_eval_confidence.py` (tín hiệu mới), `test_bm25_normalized.py` (bỏ chỉnh ngưỡng tạm của S-02).
- Số đo: `documents/rag-eval/unaccented-query/folded_*.json` + README mục "Sau S-03". Lưới trọng số {0.8, 0.5, 0.3, 0.0} × 4 biến thể ở `backend/storage/eval/unaccented-query/s03_*.json` (không commit).
- Quyết định: trọng số 0.3, ngưỡng 0.40 (bảng đánh đổi trong README). Theo luật trong plan, hit@4 bỏ dấu 236 ≥ 224 nên S-04 bị hủy, nhưng AC-04/AC-05 chưa đạt nên để user quyết định.
- Kiểm tra đã chạy: `pytest` backend toàn bộ `1704 passed, 24 skipped`.
- Còn lại/blocker: chờ user quyết định AC-04/AC-05/S-04 và phạm vi frontend `gateDecision.js`. `rag_chain._debug_chunk` chưa có `bm25_folded_norm_score`/`bm25_index` (S-05); `retrieval_debug.confidence.signals` đã có `bm25_folded_norm` qua `assess_context`.

### S-05 — agent-backend

- Cập nhật lúc: `2026-11-25T22:39:28+07:00`.
- Đã làm:
  - `generation/rag_chain.py`: `DEBUG_CHUNK_FIELDS` thêm `bm25_folded_norm_score`, `bm25_index` (có trong `retrieved_chunks`/`selected_chunks` của `retrieval_debug`).
  - `tests/test_unaccented_rag_chain.py` (AC-06): `RagChain` với `Retriever` thật (BM25 hai chỉ mục trên kho 6 chunk, embedding/vector store giả không trả kết quả), `QUERY_CORRECTION_ENABLED=true`, LLM sửa câu ném lỗi (`llm_error`) hoặc `LLMBudget(0)` (`skipped_budget`): câu `hoc phi mot tin chi la bao nhieu` có `strong_context=True`, `reason=passed`, chunk đầu `bm25_index=folded`. Ca đối chứng: tắt ngưỡng bỏ dấu thì `below_bm25_norm`.
  - Frontend (AC-07): `lib/gateDecision.js` thêm tín hiệu `bm25_folded_norm` (đánh dấu `optional`), ngưỡng `min_bm25_folded_norm_score` (mặc định 0.4), cùng luật bỏ qua `bm25_norm`/`vector` khi tín hiệu bỏ dấu đạt. `settings/RetrievalTestPanel.jsx`: `draftGateThresholds` lấy `min_bm25_folded_norm_score` từ cấu hình đã lưu (chưa có ô nháp); dòng tín hiệu bỏ dấu chỉ hiện khi câu có tín hiệu này (câu có dấu không bị thêm dòng "thiếu tín hiệu"). Test: `gateDecision.test.js` (+4 ca chép từ backend, cập nhật kỳ vọng `signals`), `RetrievalTestPanel.test.jsx` (+3).
  - R-01: `heuristic_rerank` dùng token bỏ dấu khi câu không có dấu **hoặc** có context `bm25_index == "folded"` (khớp quy tắc BM25, gồm câu thiếu dấu một phần và trường hợp rewrite chèn chữ có dấu). Test `test_heuristic_rerank_uses_folded_terms_when_bm25_ranked_on_folded_index`.
  - R-02: `guardrails.min_bm25_folded_norm_score: null` trả về giá trị `.env` (theo mẫu `min_rerank_score`), dòng ghi đè trong DB bị xóa; comment ghi rõ muốn tắt hẳn thì để trống env, 1.0 gần như tắt. Test PUT: kẹp [0, 1], bỏ trường giữ nguyên, `null` về `.env`; test persistence: `null` xóa dòng và giữ sau restart.
  - R-03: câu tóm tắt docstring `confidence.py` nêu luật từ khóa `bm25_norm` hoặc `bm25_folded_norm`.
  - Đo cuối trên `2bcdc84` (mã sạch; `dirty=true` chỉ vì `review.md` của reviewer chưa commit): 4 bộ giống từng câu lượt đo trước; thay `documents/rag-eval/unaccented-query/folded_*.json` bằng bản này, cập nhật README.
- File thay đổi: `backend/app/{generation/rag_chain.py,generation/confidence.py,retrieval/reranker.py,core/config.py,api/schemas.py}`, `backend/tests/{test_unaccented_rag_chain.py,test_bm25_folded.py,test_config_api.py,test_config_persistence.py}`, `frontend/src/lib/gateDecision{.js,.test.js}`, `frontend/src/settings/RetrievalTestPanel{.jsx,.test.jsx}`; commit `2bcdc84`; số đo + README: commit sau.
- Kiểm tra đã chạy: backend `pytest` toàn bộ `1708 passed, 24 skipped`; frontend `npm test` `48 files, 424 passed`; `npm run build` thành công.
- Còn lại/blocker: không có. Chưa đo với reranker/multi-query bật (đã ghi trong README, ngoài AC).

## Trao đổi giữa agents

### MSG-agent-backend-001

- Lúc: `2026-11-25T22:08:26+07:00`.
- Từ: `agent-backend`; đến: user (người yêu cầu).
- Nhiệm vụ: `S-03`, `S-04`, `S-05`.
- Loại: `decision`.
- Nội dung: hỏi cách xử lý AC-04/AC-05 lệch 1 câu ở ngưỡng 0.40 và có đưa `gateDecision.js` vào phạm vi không. User chọn: giữ 0.40, nới tiêu chí theo số đo, hủy S-04; thêm `gateDecision.js` vào S-05.
- Hành động mong muốn: coordinator cập nhật `task.md`/`plan.md` (đã làm); `agent-backend` làm S-05.

### MSG-agent-backend-002

- Lúc: `2026-11-25T22:39:28+07:00`.
- Từ: `agent-backend`; đến: `agent-reviewer`.
- Nhiệm vụ: `S-05`, review vòng cuối.
- Loại: `handoff`.
- Tham chiếu: `review.md` vòng 1 (bản `ff058b1`, R-01…R-03). `agent-backend` không sửa `review.md`; file này đang có thay đổi chưa commit của reviewer trong working tree chung và vẫn để nguyên.
- Nội dung:
  - R-01 đã sửa: `backend/app/retrieval/reranker.py` `heuristic_rerank` (điều kiện bỏ dấu = câu không dấu hoặc có context `bm25_index == "folded"`); test `backend/tests/test_bm25_folded.py::test_heuristic_rerank_uses_folded_terms_when_bm25_ranked_on_folded_index`.
  - R-02 đã sửa: `backend/app/core/config.py` (`null` → `_INITIAL_SETTINGS`), comment trong `backend/app/api/schemas.py`; test `test_config_api.py::test_update_folded_bm25_threshold_is_clamped_and_null_restores_env`, `test_config_persistence.py::test_folded_bm25_threshold_persists`. Tắt hẳn ở runtime vẫn không có (giống `min_bm25_norm_score`); đã ghi trong comment.
  - R-03 đã sửa: docstring đầu `backend/app/generation/confidence.py`.
  - Điều kiện approve: AC-06 (`tests/test_unaccented_rag_chain.py`), AC-07 (`DEBUG_CHUNK_FIELDS`, `gateDecision.js` + panel + test), AC-08 (pytest/npm test/build), đo cuối trên `2bcdc84`: xem `verification.md` V-06…V-08 và README.
- Hành động mong muốn: review vòng cuối diff `ff058b1..HEAD` của nhánh `feat/unaccented-query-retrieval`, xác nhận R-01…R-03 và kết luận trong `review.md`.

## Bàn giao

Chưa có.

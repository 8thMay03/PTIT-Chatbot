# Plan: 2026-11-25-unaccented-query-retrieval

## Hướng tiếp cận

Sửa theo hai lớp, lớp sau chỉ làm nếu số đo sau lớp trước chưa đạt:

1. **BM25 bỏ dấu (S-02, S-03)** — sửa trực tiếp nguyên nhân gate trượt, tất định, không gọi LLM. Giữ nguyên chỉ mục có dấu hiện tại và thêm một chỉ mục bỏ dấu song song, giống cách `PatternSet` của guardrail chạy hai lượt: câu có dấu giữ đúng kết quả cũ, chỉ câu thiếu dấu mới dùng lượt bỏ dấu. Không gộp thành một chỉ mục bỏ dấu duy nhất vì sẽ làm trùng các từ khác nghĩa (`học viện`/`học viên`, `chuyên`/`chuyển`), đổi IDF và điểm `bm25_norm` của mọi câu có dấu, buộc hiệu chỉnh lại ngưỡng RAG-18.
2. **Khôi phục dấu từ corpus (S-04, có điều kiện)** — nếu hit@4 bỏ dấu sau lớp 1 vẫn dưới mục tiêu AC-03 (embedding câu không dấu kém), thêm bước khôi phục dấu bằng bảng n-gram lấy từ chính các chunk đã index, dùng làm fallback khi LLM sửa câu tắt/lỗi. Câu đã khôi phục đi vào pipeline có dấu hiện tại nên embedding, reranker và gate không phải đổi.

Bật LLM sửa câu theo mặc định hoặc chỉ cho câu không dấu là hướng bổ sung, không thuộc task này (xem Rủi ro).

## Phân công

### S-01 — Baseline và chế độ đo `strip_partial`

- Agent: `agent-backend`
- Trạng thái: `done` (2026-11-25, xem `implementation.md` S-01)
- Mục tiêu: có số đo nền để so cho mọi AC; phục vụ `AC-01`.
- Việc cần làm:
  - Thêm `strip_partial` vào `PERTURB_MODES` của `scripts/typo_variants.py` (chỉ áp lỗi bỏ dấu một phần, cùng seed). Test trong `tests/test_typo_variants*.py` hoặc file test hiện có của module.
  - Chạy `python -m scripts.eval_confidence` trên 3 fixture × 4 chế độ `none|strip_all|strip_partial|typo`, cờ sửa câu tắt, seed `20261121`, lưu `documents/rag-eval/unaccented-query/baseline_<perturb>.json`.
  - Chạy `python -m scripts.eval_retrieval --mode hybrid` và `--mode bm25` với `--perturb strip_all` để tách phần do BM25 và phần do vector.
  - Ghi `documents/rag-eval/unaccented-query/README.md`: commit, cấu hình, bảng gate/hit@4/phân bố `bm25_norm`.
- Phạm vi file được sửa: `backend/scripts/typo_variants.py`, test tương ứng, `documents/rag-eval/unaccented-query/*`.
- Phụ thuộc: Postgres + corpus D26 đã index, API key embedding.
- Đầu ra/bàn giao: file baseline + README; cập nhật `verification.md` V-01.
- Người nhận: `agent-backend`.

### S-02 — Chỉ mục BM25 bỏ dấu và quy tắc chọn chỉ mục

- Agent: `agent-backend`
- Trạng thái: `done` (2026-11-25, xem `implementation.md` S-02)
- Mục tiêu: câu thiếu dấu có xếp hạng keyword và `bm25_norm` có nghĩa; câu có dấu không đổi; phục vụ `AC-02`, `AC-03`, `AC-05`.
- Việc cần làm:
  - `bm25.py`: thêm `_tokenize_folded(text)` = `_tokenize(strip_accents(text))` (dùng `app.guardrails.normalization.strip_accents`, đã xử lý NFC/NFD và `đ`). `_ensure_index` dựng thêm `BM25Okapi` trên token bỏ dấu cùng snapshot, cùng cơ chế `invalidate_bm25_cache` (corpus ~1000 chunk, bộ nhớ ×2 chấp nhận được).
  - `search()` tính cả hai điểm khi cần và trả mỗi kết quả các trường: `bm25_norm_score` (chỉ mục có dấu, giữ nguyên ý nghĩa), `bm25_folded_norm_score` (chỉ mục bỏ dấu, `None` nếu không tính), `bm25_index` (`accented|folded`, chỉ mục quyết định thứ hạng).
  - Quy tắc chọn thứ hạng (bản đầu, chỉnh theo số đo S-03): câu không có dấu (`has_accents` sai) → xếp theo chỉ mục bỏ dấu; câu có dấu → xếp theo chỉ mục có dấu như hiện tại, chỉ chuyển sang bỏ dấu khi top-1 `bm25_norm_score` có dấu dưới ngưỡng gate (bắt câu bỏ dấu một phần). Câu có dấu đạt ngưỡng giữ nguyên kết quả từng byte.
  - `hybrid.py`, `retrieval/multi_query.py`: mang thêm `bm25_folded_norm_score` (max qua các truy vấn như `bm25_norm_score`) và `bm25_index`.
  - `reranker.py` `heuristic_rerank`: tính `term_coverage` trên token bỏ dấu khi câu không có dấu (chỉ ảnh hưởng thứ tự heuristic, không phải gate).
- Phạm vi file được sửa: `backend/app/retrieval/bm25.py`, `hybrid.py`, `multi_query.py`, `parent_child.py` (bổ sung khi làm: gộp chunk cha phải mang trường mới), `reranker.py` (chỉ `heuristic_rerank`/`_tokenize`), `backend/tests/test_bm25_normalized.py` + test mới.
- Phụ thuộc: S-01 xong (có baseline trước khi đổi mã).
- Đầu ra/bàn giao: hợp đồng trường kết quả ở mục dưới; test đơn vị: `hoc phi` khớp chunk `học phí`, câu có dấu cho cùng thứ hạng/điểm như trước, chọn chỉ mục đúng ba trường hợp (có dấu đạt, có dấu dưới ngưỡng, không dấu).
- Người nhận: `agent-backend` (S-03).

### S-03 — Hiệu chỉnh ngưỡng và cập nhật gate

- Agent: `agent-backend`
- Trạng thái: `todo`
- Mục tiêu: gate dùng được tín hiệu bỏ dấu với ngưỡng đã đo, không mở cho câu không đáp án; phục vụ `AC-03`, `AC-04`, `AC-07`.
- Việc cần làm:
  - Đo phân bố `bm25_folded_norm_score` top-1 trên `ptit_rag_300`/`ptit_faq` (`strip_all`, `strip_partial`) và `ptit_no_answer_56` (`none`, `strip_all`) bằng `eval_confidence --sweep` (bổ sung sweep cho trường mới nếu chưa có). Chọn `RETRIEVAL_MIN_BM25_FOLDED_NORM_SCORE` theo cùng cách RAG-18: không cho thêm câu `near_miss`/`in_domain_missing` qua so với bản có dấu.
  - `confidence.py`: tín hiệu `bm25` đạt khi `bm25_norm ≥ min_bm25_norm_score` **hoặc** `bm25_folded_norm ≥ min_bm25_folded_norm_score`; `signals` thêm `bm25_folded_norm`; `GateThresholds` thêm ngưỡng mới; `reason` khi trượt vẫn là `below_bm25_norm`.
  - Điểm quyết định: nếu đo cho thấy cho phép tín hiệu bỏ dấu với **câu có dấu** làm tăng câu không đáp án qua gate (vi phạm AC-02), giới hạn tín hiệu bỏ dấu cho câu được S-02 xếp theo chỉ mục bỏ dấu (`bm25_index == folded`) và đo lại. Ghi quyết định trong `implementation.md`.
  - `config.py`: field `retrieval_min_bm25_folded_norm_score` (env + runtime config `guardrails.min_bm25_folded_norm_score`, kẹp [0, 1], hiển thị trong snapshot cấu hình như `min_bm25_norm_score`). Cập nhật docstring đầu `confidence.py` và `.env.example` nếu có mục gate.
  - Chạy lại đo đầy đủ (4 chế độ × 3 fixture), lưu `documents/rag-eval/unaccented-query/folded_<perturb>.json`, cập nhật README.
- Phạm vi file được sửa: `backend/app/generation/confidence.py`, `backend/app/core/config.py`, `backend/scripts/eval_confidence.py`, `backend/tests/test_retrieval_confidence.py`, `backend/tests/test_eval_confidence.py`, `.env.example` (nếu có mục liên quan), `documents/rag-eval/unaccented-query/*`.
- Phụ thuộc: S-02.
- Đầu ra/bàn giao: ngưỡng + số đo; kết luận có cần S-04 hay không (hit@4 `strip_all` so với 224/300).
- Người nhận: coordinator quyết định S-04.

### S-04 — Khôi phục dấu tất định từ corpus (chỉ làm nếu S-03 chưa đạt AC-03 về hit@4)

- Agent: `agent-backend`
- Trạng thái: `todo` (có điều kiện)
- Mục tiêu: câu không dấu có bản có dấu để embedding/reranker dùng khi không có LLM; phục vụ `AC-03`, `AC-06`.
- Việc cần làm:
  - Module mới `backend/app/retrieval/diacritics.py`: dựng từ snapshot chunk của BM25 (dùng chung generation cache) bảng đếm `folded n-gram (1–3) → dạng có dấu`; khôi phục câu bằng quy hoạch động chọn chuỗi n-gram có tần suất cao nhất, chỉ thay chữ không dấu có trong bảng, giữ nguyên chữ có số/viết hoa toàn bộ (cùng quy tắc `protected_tokens` của `query_corrector.py`) và chữ không có trong corpus.
  - `QueryCorrector.correct` / `rag_chain.py`: khi kết quả LLM là `disabled|not_configured|llm_error|skipped_budget` và câu thiếu dấu, dùng câu khôi phục với `reason = restored_from_corpus`; câu khôi phục vẫn qua `check_scope` lần hai như câu LLM sửa. Câu trả lời vẫn sinh từ câu gốc (giữ hành vi hiện tại).
  - Đo độ chính xác khôi phục (so với `original_question`) và gate/hit@4 trên `strip_all`/`strip_partial`; lưu `restore_<perturb>.json`.
- Phạm vi file được sửa: `backend/app/retrieval/diacritics.py` (mới), `backend/app/generation/query_corrector.py` (chỉ nhánh fallback), `backend/app/generation/rag_chain.py` (nếu cần), test mới, `documents/rag-eval/unaccented-query/*`.
- Phụ thuộc: S-03 kết luận cần làm.
- Đầu ra/bàn giao: module + số đo; nếu bỏ qua, coordinator ghi `cancelled` kèm số đo lý do.
- Người nhận: `agent-backend` (S-05).

### S-05 — Test fallback LLM, debug và đo cuối

- Agent: `agent-backend`
- Trạng thái: `todo`
- Mục tiêu: chứng minh không còn phụ thuộc LLM và mọi AC có bằng chứng; phục vụ `AC-06`, `AC-07`, `AC-08`.
- Việc cần làm:
  - Test `RAGChain` với provider LLM giả ném lỗi và với budget đã cạn: câu `hoc phi mot tin chi la bao nhieu` trên corpus fixture vẫn `strong_context=True`.
  - Kiểm `retrieval_debug.confidence.signals` có `bm25_folded_norm`, chunk debug có `bm25_index`; nếu UI admin hiển thị signals theo danh sách cố định thì báo coordinator trước khi sửa frontend.
  - Chạy `pytest` toàn bộ backend (Postgres Docker lên), chạy lại bộ đo cuối trên bản tích hợp.
- Phạm vi file được sửa: test backend; `backend/app/generation/rag_chain.py` chỉ nếu cần đưa trường debug.
- Phụ thuộc: S-03 (và S-04 nếu làm).
- Đầu ra/bàn giao: `verification.md` V-01…V-08.
- Người nhận: reviewer.

## Hợp đồng dùng chung

- Kết quả BM25/hybrid/multi-query (dict chunk) thêm: `bm25_folded_norm_score: float | None`, `bm25_index: "accented" | "folded" | None`. `bm25_norm_score` giữ nguyên ý nghĩa (chỉ mục có dấu) để báo cáo RAG-18 và script cũ đọc đúng.
- `ConfidenceDecision.signals` thêm khóa `bm25_folded_norm`; `GateThresholds` thêm `min_bm25_folded_norm_score: float | None` (`None` = không dùng). Schema báo cáo `eval_confidence` tăng `schema_version` nếu đổi cấu trúc.
- Runtime config: khóa mới `guardrails.min_bm25_folded_norm_score`; không đổi khóa cũ.
- `QueryCorrectionResult.reason` thêm giá trị `restored_from_corpus` (chỉ khi làm S-04).
- File mã nguồn dùng chung và người sửa: toàn bộ do `agent-backend` sửa tuần tự; `rag_chain.py`, `config.py` là file dùng chung với task khác — kiểm tra nhánh đang mở trước khi sửa.
- Lượt ghi năm file task: `agent-backend` ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `agent-backend`; phạm vi: AC-01…AC-08.
- Reviewer: `agent-backend` hoặc agent khác do user chỉ định; phạm vi: diff S-02…S-05, số đo trong `documents/rag-eval/unaccented-query/`.
- Hình thức review: `self_review` nếu chỉ một agent; ghi rõ.
- Người xử lý nhận xét: `agent-backend`.

## Thứ tự tích hợp và kiểm chứng

1. Tạo nhánh `feat/unaccented-query-retrieval` từ `dev` mới nhất; S-01 đo baseline trước khi đổi mã ứng dụng.
2. S-02 → S-03 tuần tự (S-03 cần trường mới của S-02 để đo).
3. Coordinator đọc số đo S-03: hit@4 `strip_all` ≥ 224/300 → hủy S-04; ngược lại làm S-04.
4. S-05 test và đo cuối trên bản tích hợp; verifier ghi V-*.
5. Review, sửa nhận xét bắt buộc, đo lại phần bị ảnh hưởng; coordinator đóng task khi `approved`. Commit message tiếng Anh, ví dụ `feat: add accent-folded BM25 index for unaccented queries`.

## Rủi ro và điều chỉnh kế hoạch

- **Câu có dấu bị ảnh hưởng ngầm**: quy tắc fallback sang chỉ mục bỏ dấu khi điểm có dấu thấp có thể cho câu không đáp án có dấu qua gate. Chặn bằng AC-02 và điểm quyết định ở S-03.
- **Trùng nghĩa khi bỏ dấu** (`ban`/`bản`/`bạn`, `hoc vien`): làm điểm BM25 bỏ dấu cao giả. Ngưỡng bỏ dấu đo riêng (S-03), không dùng chung 0.25; theo dõi `near_miss` bỏ dấu.
- **Embedding câu không dấu yếu** (median cosine 0.44): BM25 bỏ dấu không sửa được thứ hạng vector; S-04 là phương án dự phòng, có số đo quyết định.
  - 2026-11-25 (sau S-01): nhánh vector riêng tụt hit@4 226 → 51 với câu bỏ dấu dù cosine vẫn vượt 0.37 ở 289/300 câu, tức tín hiệu vector của gate không phân biệt được câu bỏ dấu trúng/trật. S-03 phải đo thêm phương án giảm `hybrid_vector_weight` cho câu được xếp theo chỉ mục bỏ dấu (trong phạm vi `retriever.py`/`hybrid.py`), và nhiều khả năng cần S-04. Thêm `backend/app/retrieval/retriever.py` vào phạm vi file của S-02/S-03 cho phương án này.
- **Khôi phục dấu sai nghĩa** (S-04): giống rủi ro đã thấy ở LLM (`Học viên` thay `Học viện`); bảng n-gram theo corpus PTIT ưu tiên cụm hay gặp trong tài liệu nên có lợi thế ở miền này, nhưng phải đo độ chính xác và chỉ dùng cho truy xuất, không hiển thị cho người dùng.
- **Corpus đổi**: hai chỉ mục và bảng n-gram cùng vô hiệu theo `invalidate_bm25_cache`; ngưỡng phải đo lại khi kho đổi nhiều như ngưỡng RAG-18.
- **Hướng bổ sung ngoài phạm vi**: chế độ `QUERY_CORRECTION_ENABLED` chỉ gọi LLM cho câu thiếu dấu (giảm chi phí để có thể bật mặc định); thêm biến thể không dấu cho `evaluate_ragas` (`--perturb`) để đo chất lượng câu trả lời. Đề xuất thành task riêng sau khi task này xong.

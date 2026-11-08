# Plan: 2026-11-08-rag18-confidence-gate

Nhánh: `feat/rag18-confidence-gate` tách từ `dev` đã cập nhật. Mặc định một agent (`agent-claude`) làm tuần tự các nhiệm vụ; nếu có thêm agent, S-01 và S-02 chạy song song được vì không chung file.

## Phân công

### S-01 — Tập câu không có đáp án

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: fixture ≥ 50 câu `answerable: false`; phục vụ `AC-01`, là đầu vào cho `AC-02`, `AC-03`.
  - Phân bổ đề xuất: ~25 câu cùng miền PTIT/sinh viên nhưng Sổ tay D26 và các dataset đang index không có thông tin (ví dụ chính sách, con số, thủ tục không tồn tại); ~15 câu gần nghĩa với nội dung có thật nhưng hỏi chi tiết không có (dễ vượt gate nhất); ~10 câu ngoài miền nhưng lọt scope guardrail. Tối thiểu 70% câu phải qua `check_scope`.
  - Mỗi câu kiểm không có đáp án bằng cách tìm từ khóa chính trong bản converted của các tài liệu đang index (cùng nguồn task `2026-11-07-rag-testset-300` đã dùng) và đọc top-10 retrieval; ghi lại cách kiểm trong `implementation.md`.
- Phạm vi file được sửa: `backend/tests/fixtures/ptit_no_answer_50.json` (mới), `backend/tests/test_no_answer_set.py` (mới).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: fixture + test lint (schema, id duy nhất, không trùng câu hỏi với `ptit_rag_300.json`/`ptit_ragas_100.json`, phân bổ `category`, tỉ lệ qua `check_scope`).
- Người nhận: `agent-claude` (S-04).

### S-02 — Tín hiệu BM25 chuẩn hóa

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: mỗi kết quả BM25 có thêm `bm25_norm_score` trong [0, 1] và trường này đi qua hybrid → multi-query → parent-child như `bm25_score`; phục vụ `AC-05` và là tín hiệu cho `AC-02`.
- Phạm vi file được sửa: `backend/app/retrieval/bm25.py`, `backend/app/retrieval/hybrid.py`, `backend/app/retrieval/multi_query.py`, `backend/app/retrieval/parent_child.py`, `backend/tests/test_hybrid_retrieval.py`, `backend/tests/test_multi_query.py`, test mới `backend/tests/test_bm25_normalized.py`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: hợp đồng `bm25_norm_score` (mục Hợp đồng dùng chung); test chứng minh giá trị nằm trong [0, 1], bằng 1 khi chunk chứa đủ term với tf bão hòa, và ổn định hơn điểm thô khi nhân bản kho.
- Người nhận: `agent-claude` (S-03, S-05).

### S-03 — Script đo tín hiệu và quét ngưỡng

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: `python -m scripts.eval_confidence` chạy pipeline giống `eval_retrieval --mode full` (rewrite/multi-query theo luật, rerank theo cấu hình) cho golden set và tập không có đáp án; ghi cho từng câu: kết quả `check_scope`, top-1 của `vector_score`, `bm25_score`, `bm25_norm_score`, `rerank_score`, hit@4 (với câu có `expected_terms`), quyết định của gate hiện tại và gate mới. Xuất JSON (kèm snapshot cấu hình, embedding model, reranker provider, fingerprint kho, sha256 dataset, git commit) và bảng percentile/histogram dạng text; có `--sweep` quét lưới ngưỡng cho từng luật kết hợp (OR hiện tại, từng tín hiệu riêng, AND, tổng có trọng số) và in tỉ lệ từ chối đúng/từ chối nhầm. Phục vụ `AC-02`.
- Phạm vi file được sửa: `backend/scripts/eval_confidence.py` (mới), `backend/tests/test_eval_confidence.py` (mới, test phần tính toán thuần với dữ liệu giả, không cần DB/API).
- Phụ thuộc: S-02 (hợp đồng trường; có thể viết trước với dữ liệu giả). Tái dùng hàm của `scripts/eval_retrieval.py` (`build_retrieval_fn`, cache embedding, `snapshot_*`, `git_info`, `first_hit_rank`) bằng import, không sửa file đó trừ khi cần tách hàm; nếu phải sửa thì ghi vào `implementation.md` và chạy lại `test_eval_retrieval.py`.
- Đầu ra/bàn giao: script + test; hướng dẫn chạy ghi trong `implementation.md`.
- Người nhận: `agent-claude` (S-04).

### S-04 — Đo phân bố và chọn luật/ngưỡng

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: chạy S-03 trên index local (`ptit_rag_300.json`, `ptit_ragas_100.json`, `ptit_no_answer_50.json`); chọn luật kết hợp và ngưỡng theo mục tiêu: từ chối nhầm golden ≤ 5% trước, rồi tối đa tỉ lệ từ chối đúng (≥ 80%). Ghi quyết định (luật, ngưỡng, lý do, các phương án bị loại) thành `MSG-agent-claude-*` loại `decision` trong `implementation.md`. Phục vụ `AC-02`, là đầu vào cho S-05.
  - Nếu không luật nào đạt đồng thời AC-03 và AC-04 với reranker `heuristic`: đo thêm reranker `cross-encoder` (`rerank_score` tuyệt đối). Nếu vẫn không đạt, dừng và báo người dùng kèm đường cong đánh đổi; không tự nới tiêu chí.
- Phạm vi file được sửa: `documents/rag-eval/rag-18/` (báo cáo JSON nháp); không sửa mã.
- Phụ thuộc: S-01, S-02, S-03 xong; có index local + embedding cache/API key.
- Đầu ra/bàn giao: báo cáo nháp + quyết định ngưỡng.
- Người nhận: `agent-claude` (S-05).

### S-05 — Gate mới và cấu hình

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: thay logic `has_strong_context` bằng gate theo quyết định S-04; ngưỡng vector theo embedding model; cấu hình tương thích ngược; đưa tín hiệu và lý do của gate vào `retrieval_debug`. Phục vụ `AC-05`, `AC-06`.
- Phạm vi file được sửa: `backend/app/generation/confidence.py`, `backend/app/generation/rag_chain.py` (chỉ đoạn gọi gate và `retrieval_debug`), `backend/app/core/config.py`, `backend/app/core/config_store.py`, `backend/app/api/schemas.py`, `.env.example`, `backend/tests/test_retrieval_confidence.py`, `backend/tests/test_rag_chain.py`, `backend/tests/test_config_api.py`, `backend/tests/test_config_persistence.py`.
- Phụ thuộc: S-02 (tín hiệu), S-04 (luật + ngưỡng). Phần khung (dataclass, cấu hình, tương thích ngược) làm được trước S-04.
- Đầu ra/bàn giao: gate + test; ghi chú hành vi khi dùng model chưa hiệu chỉnh.
- Người nhận: `agent-claude` (S-06).

### S-06 — Đo lại với gate thật, báo cáo cuối

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: chạy lại `eval_confidence` với gate đã cài (không phải mô phỏng trong sweep) để lấy số cuối cho `AC-03`, `AC-04`; chạy `eval_retrieval --mode full` so với báo cáo gần nhất để xác nhận S-02 không đổi thứ hạng. Hoàn thiện `documents/rag-eval/rag-18/` và thêm mục "RAG-18" vào `documents/rag-eval/README.md` (bảng phân bố, bảng quét ngưỡng, ngưỡng chọn, giới hạn). Phục vụ `AC-02`, `AC-03`, `AC-04`.
- Phạm vi file được sửa: `documents/rag-eval/rag-18/*`, `documents/rag-eval/README.md`.
- Phụ thuộc: S-05.
- Đầu ra/bàn giao: báo cáo cuối; bàn giao verifier/reviewer.
- Người nhận: `agent-claude` (verifier), reviewer.

## Hợp đồng dùng chung

- **`bm25_norm_score`** (S-02 cung cấp; S-03, S-05 sử dụng):
  - `BM25Search.search` gán cho mỗi kết quả `bm25_norm_score = raw / upper_bound(query)`, với `upper_bound = Σ_{t ∈ term duy nhất của query} idf(t) · (k1 + 1)`, là cận trên lý thuyết của BM25 Okapi theo query; kẹp vào [0, 1]. Query không có term nào thì không trả kết quả (như hiện tại).
  - Term không có trong từ vựng kho: S-02 cài hai biến thể sau cờ nội bộ (`bỏ khỏi mẫu số` / `tính với idf của df = 1`). S-04 chọn theo số đo; biến thể bị loại phải bị xóa trước review.
  - `hybrid.py` chép trường giống `bm25_score`; `multi_query.py`, `parent_child.py` gộp bằng max giống `bm25_score`. Kết quả chỉ từ vector có `bm25_norm_score = None`.
  - Giữ nguyên `bm25_score` thô (debug và reranker heuristic vẫn dùng).
- **Gate** (S-05 cung cấp; `rag_chain.py`, `eval_confidence.py` sử dụng):
  - `assess_context(contexts, thresholds) -> ConfidenceDecision`; `ConfidenceDecision` gồm `strong: bool`, `reason: str` (ví dụ `vector_and_bm25`, `below_thresholds`, `no_context`, `uncalibrated_model`), `signals: dict[str, float | None]` (top-1 của từng tín hiệu). Tín hiệu top-1 = max trên các context sau rerank.
  - `rag_chain` giữ khóa `strong_context` (bool) trong `result` và `retrieval_debug` cho `routes.py`; thêm `retrieval_debug["confidence"] = {"reason", "signals", "thresholds"}`. `routes.py` không cần sửa.
  - `has_strong_context` được xóa hoặc chuyển thành wrapper mỏng; nếu xóa, cập nhật mọi import (`rg has_strong_context`).
- **Cấu hình** (S-05):
  - Ngưỡng vector theo model: bảng mặc định trong `confidence.py` khóa theo tên embedding model (giá trị từ S-04); `RETRIEVAL_MIN_VECTOR_SCORE` nếu được đặt rõ ràng thì ghi đè. Model không có trong bảng và không có ghi đè: log cảnh báo một lần, `reason=uncalibrated_model` trong debug, gate chỉ dùng các tín hiệu không phụ thuộc model.
  - BM25: biến mới `RETRIEVAL_MIN_BM25_NORM_SCORE` (thang [0, 1]). `RETRIEVAL_MIN_BM25_SCORE`/`min_bm25_score` vẫn được nhận (API, env, runtime config đã lưu) nhưng không còn dùng trong gate; ghi rõ deprecated trong `.env.example`.
  - API `/config` (`GuardrailsConfigPayload`, `UpdateGuardrailsConfig`): giữ trường cũ, thêm trường mới là tùy chọn. Runtime config đã lưu `retrieval_min_vector_score = 0.30` sẽ ghi đè bảng theo model: S-05 phải quyết định và ghi lại cách xử lý (ví dụ chỉ coi là ghi đè khi khác giá trị mặc định cũ, hoặc hướng dẫn xóa) kèm test.
- File mã nguồn dùng chung và người sửa: tất cả do `agent-claude` sửa tuần tự theo thứ tự trên. `rag_chain.py` chỉ S-05 sửa; `eval_retrieval.py` không ai sửa trừ khi S-03 ghi lý do.
- Lượt ghi năm file task: coordinator `agent-claude` ghi tuần tự; agent khác (nếu có) gửi nội dung qua mục trao đổi trong `implementation.md`.

## Phân công kiểm chứng và review

- Verifier: `agent-claude`; phạm vi: `AC-01`…`AC-06`, chạy toàn bộ `python -m pytest` trong `backend`, test frontend liên quan cấu hình (`ConfigView.cache.test.jsx`, `admin/AdminApp.test.jsx`) và hai lệnh đo ở S-06.
- Reviewer: ưu tiên reviewer độc lập do người dùng chỉ định; nếu không có, `agent-claude` ghi `self_review`. Phạm vi: diff toàn nhánh, báo cáo `documents/rag-eval/rag-18/`, fixture S-01 (kiểm ngẫu nhiên ≥ 10 câu xem thật sự không có đáp án).
- Hình thức review: `independent` nếu có reviewer khác, ngược lại `self_review` (ghi rõ trong `review.md`).
- Người xử lý nhận xét: `agent-claude` cho mọi `S-*`; reviewer xác nhận sau khi sửa.

## Thứ tự tích hợp và kiểm chứng

1. Tạo nhánh `feat/rag18-confidence-gate` từ `dev`; ghi commit nền vào `implementation.md`. S-01 và S-02 làm độc lập, mỗi nhiệm vụ một commit.
2. S-03 sau khi hợp đồng `bm25_norm_score` của S-02 đã commit; chạy `pytest tests/test_eval_confidence.py tests/test_eval_retrieval.py`.
3. S-04 chạy đo, ghi quyết định; xóa biến thể BM25 bị loại.
4. S-05 cài gate + cấu hình; chạy toàn bộ backend pytest.
5. S-06 đo lại bằng gate thật, hoàn thiện báo cáo; chuyển task sang `in_review`.
6. Verifier điền `verification.md` (V-01…V-06 tương ứng AC); reviewer ghi `review.md`; agent sửa `R-*` bắt buộc, verifier chạy lại phần bị ảnh hưởng.
7. Coordinator đối chiếu AC, review `approved` trên bản mới nhất, mở PR vào `dev`, cập nhật trạng thái thẻ Notion RAG-18, rồi chuyển task `done`.

## Rủi ro và điều chỉnh kế hoạch

- **AC-04 xung đột với retrieval trượt**: khoảng 10% câu golden trượt hit@10, nên gate từ chối những câu này là đúng về hành vi nhưng vẫn bị tính là từ chối nhầm. Cách xử lý: báo cáo cả tỉ lệ trên nhóm hit@4; nếu chỉ đạt AC-04 trên nhóm hit@4, dừng và hỏi người dùng có điều chỉnh định nghĩa AC-04 không (coordinator ghi vào lịch sử quyết định của `task.md`).
- **Scope guardrail che gate**: câu ngoài miền bị `check_scope` chặn trước khi tới gate. Đã xử lý bằng yêu cầu ≥ 70% câu lọt scope và báo cáo gate-only. Nếu RAG-19 đổi scope guardrail sau này, cần đo lại.
- **Reranker heuristic không cho điểm tuyệt đối**: `rerank_score` heuristic là min-max trong danh sách ứng viên, không dùng làm ngưỡng. Chỉ đưa `rerank_score` vào gate khi provider là `cross-encoder`; thêm provider khác thì phải hiệu chỉnh lại.
- **Overfit ngưỡng**: tập không có đáp án nhỏ (~50 câu). Báo cáo khoảng an toàn quanh ngưỡng chọn (tỉ lệ ở ngưỡng ±10%), chọn điểm nằm ở vùng ổn định thay vì điểm tối ưu sát biên.
- **Index local khác `.env.example`**: số đo phụ thuộc index và `.env` local; báo cáo phải ghi snapshot cấu hình và fingerprint. Kho thay đổi (thêm tài liệu) thì cần đo lại; ghi điều này trong README.
- **Runtime config đã lưu**: xem mục Cấu hình. Không xử lý thì gate mới có thể bị ghi đè âm thầm bởi giá trị 0.30/2.0 cũ.
- **Tập không có đáp án trùng với RAG-25**: dùng trường `answerable`, `category` để RAG-25 gộp được; nếu RAG-25 chốt schema khác trước khi task này xong, coordinator điều chỉnh S-01.

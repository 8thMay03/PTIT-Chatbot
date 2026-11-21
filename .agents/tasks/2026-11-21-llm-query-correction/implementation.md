# Implementation: 2026-11-21-llm-query-correction

## Tổng quan triển khai

Nhánh `feat/llm-query-correction` (tách từ `dev` tại `f3d01bd`). S-01 … S-03 xong; S-04 đã có bộ sinh lỗi gõ, script và số đo; S-05 đã cập nhật README và gửi MSG. Giá trị mặc định của cờ chờ người dùng chốt (AC-05).

## Nhật ký theo nhiệm vụ

### S-01 — agent-rag

- Cập nhật lúc: `2026-11-21T15:25:00+07:00`.
- Đã làm: module `QueryCorrector.correct(question, budget=None) -> QueryCorrectionResult(text, corrected, reason, llm_output)`; prompt + 5 ví dụ few-shot (có câu đúng giữ nguyên, câu có viết tắt/mã môn); `validate_correction`, `comparison_key`, `protected_tokens`, `levenshtein` (tự viết, có dừng sớm theo ngưỡng). Prompt đặt trong module (giống `REWRITE_SYSTEM_PROMPT`), không sửa `prompts.py`.
- File thay đổi: `backend/app/generation/query_corrector.py` (mới), `backend/tests/test_query_corrector.py` (mới).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác:
  - `reason`: `corrected`, `unchanged`, `too_different` (điều kiện 1), `protected_token_changed` (2), `invalid_output` (3), `llm_error`, `skipped_no_letters`, `skipped_budget`, `disabled`, `not_configured`. Thứ tự kiểm: điều kiện 3 → 2 → 1 (đầu ra quá dài bị bỏ ở điều kiện 3 trước khi tính Levenshtein).
  - Ngưỡng: `max(MIN_EDIT_DISTANCE=3, int(0.2 * len(key(input))))`, `MAX_LENGTH_FACTOR=2`. Không thêm `QUERY_CORRECTION_MAX_EDIT_RATIO`: số đo S-04 không cho thấy cần chỉnh (xem S-04).
  - `unchanged` khi đầu ra chỉ khác câu gốc ở chuẩn Unicode (NFD/NFC) hoặc khoảng trắng; khi đó `text` là câu gốc nguyên văn để cờ bật + LLM trả nguyên văn cho kết quả rewrite giống hệt.
  - Chữ được bảo vệ: token `\w+` có chữ số hoặc viết hoa toàn bộ ≥ 2 ký tự, so trên tập token của đầu ra (không so chuỗi con, để `INT1340` không khớp `INT13400`). Hệ quả: câu gõ hoa toàn bộ (`HOC PHI BAO NHIEU`) không sửa được vì mọi chữ đều được bảo vệ — chấp nhận.
  - `max_tokens = max(64, min(512, 2 * len(question)))`.
  - Phát hiện khi thử LLM thật (`qwen3.8-27b` qua OpenAI-compatible): model thinking dùng hết `max_tokens` cho phần suy luận, nội dung trả về rỗng/cụt (7/9 câu thử `invalid_output`, có câu 16 s). Thêm `_no_thinking_kwargs`: chỉ với `OpenAICompatibleProvider`, gửi `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`. Sau khi thêm, 11/11 câu thử cho đầu ra đúng, phần lớn 0,3–1 s. Không sửa file provider (ngoài phạm vi). Server không hiểu khóa này mà trả lỗi thì bước sửa câu rơi về câu gốc (`llm_error`). Lưu ý cho task khác: rewrite/multi-query bằng LLM (`max_tokens` 100/180) có cùng rủi ro với model thinking.
- Kiểm tra đã chạy: `pytest tests/test_query_corrector.py` (59 test, đạt).
- Còn lại/blocker: không.
- Bổ sung `2026-11-21T16:44:32+07:00` (sửa R-07, R-08 của review vòng 2): `_clean_output(output, question)` bỏ ngoặc bao ngoài (`"`, `'`, `` ` ``, `“…”`) và nhãn mở đầu (`Câu đã sửa:`, `câu hỏi được sửa lại:`, `Đã sửa:`, `Sửa lại:`, `Kết quả:`, `Corrected question:`, `Output:`…, không phân biệt hoa thường) **chỉ khi câu gốc không có sẵn ngoặc/nhãn đó**. Thứ tự: ngoặc → nhãn → ngoặc. Nhờ vậy câu người dùng tự gõ trong ngoặc mà LLM trả nguyên văn vẫn là `unchanged`, và nhãn không còn lọt vào truy vấn ở câu dài. Thêm 11 test (`test_user_quoted_question_*`, `test_label_prefix_*`). Chạy lại kiểm tra đầu ra mới trên 1 121 đầu ra LLM thật đã lưu trong `on_none.json`, `on_strip_all.json`, `on_typo.json`: 0 quyết định thay đổi, nên số đo V-06 vẫn đúng với mã mới, không cần đo lại.

### S-02 — agent-rag

- Cập nhật lúc: `2026-11-21T15:25:00+07:00`.
- Đã làm: `query_correction_enabled` (`QUERY_CORRECTION_ENABLED`, mặc định `False`) trong `Settings`; xuất trong `config_payload()["retrieval"]`; nhận ở `update_runtime_config` (bỏ qua `None`); thêm vào `PERSISTED_FIELDS`; trường trong `RetrievalConfigPayload` và `UpdateRetrievalConfig`; thêm vào `CONFIG_FIELDS` của `eval_retrieval` để báo cáo ghi cờ; thêm dòng mẫu vào `.env.example` (ngoài danh sách file của plan nhưng là tài liệu cấu hình của cờ).
- File thay đổi: `backend/app/core/config.py`, `backend/app/core/config_store.py`, `backend/app/api/schemas.py`, `backend/scripts/eval_retrieval.py`, `.env.example`, `backend/tests/test_config_api.py`, `backend/tests/test_config_persistence.py`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: hợp đồng như `plan.md` (`retrieval.query_correction_enabled: bool`, PUT nhận `bool | None`). Giá trị mặc định: giữ `false` cho tới khi người dùng chốt theo số đo AC-06.
- Kiểm tra đã chạy: `pytest tests/test_config_api.py tests/test_config_persistence.py` (41 test, đạt).
- Còn lại/blocker: người dùng chốt giá trị mặc định (AC-05).

### S-03 — agent-rag

- Cập nhật lúc: `2026-11-21T15:25:00+07:00`.
- Đã làm:
  - `VietnameseQueryRewriter(llm_provider=None, query_corrector=None)`; thêm `correct(question, budget=None)`; `rewrite(question, history=None, budget=None, correction=None) -> str` (chữ ký cũ vẫn dùng được). `correction=None` thì tự sửa câu; có `correction` thì dùng sẵn, không gọi LLM lần nữa. Bước sửa câu chạy trên câu gốc trước `rule_based_rewrite`; rewrite bằng LLM (nếu bật) nhận câu đã qua rule-based của câu đã sửa.
  - `rag_chain.iter_retrieve_context`: guardrail câu gốc → `correct()` → nếu guardrail bật và `corrected` thì `check_scope(corrected_text)`; bị chặn → phát `query_rewrite` (có trường sửa câu, `rewritten_query` rỗng) rồi trả kết quả chặn với `retrieval_debug.guardrail = {"allowed": false, "reason": ..., "stage": "corrected"}`, không truy xuất, `answer()` trả `OUT_OF_SCOPE_ANSWER`. Không phát event `guardrail` thứ hai (đúng hợp đồng plan). Kiểm lần hai chạy trước rewrite để rewrite bằng LLM không nhận câu bị chặn.
  - `query_rewrite.detail` và `retrieval_debug` thêm `query_corrected`, `corrected_query` (rỗng nếu không sửa), `correction_reason`. `elapsed_ms` của bước `query_rewrite` gồm cả thời gian sửa câu.
  - Câu trả lời vẫn sinh từ `question` gốc.
- File thay đổi: `backend/app/generation/query_rewriter.py`, `backend/app/generation/rag_chain.py`, `backend/tests/test_rag_chain.py`, `backend/tests/test_config_api.py` (rewriter giả kế thừa `VietnameseQueryRewriter` để có `correct()` và nhận `correction`).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: rewriter tùy biến truyền vào `RagChain` phải có `correct()` và nhận `correction=` (cách đơn giản: kế thừa `VietnameseQueryRewriter`). Trong repo chỉ có 3 rewriter giả trong test, đã cập nhật.
- Kiểm tra đã chạy: `pytest tests/test_rag_chain.py tests/test_query_rewriter.py tests/test_config_api.py tests/test_llm_budget.py` đạt; pytest toàn bộ đạt (xem V-08).
- Còn lại/blocker: không.

### S-04 — agent-rag

- Cập nhật lúc: `≤ 2026-11-21T16:09:08+07:00`.
- Đã làm:
  - Bộ sinh lỗi gõ `backend/scripts/typo_variants.py` (hàm thuần, `random.Random` truyền vào): `strip_all`, `strip_partial`, `wrong_tone`, `telex_leftover` (`to_telex`), `char_noise`, `merge_words`, `drop_punct`; `make_typo_variant` áp 1–3 loại khác nhau, thứ tự ngẫu nhiên, bỏ loại không áp dụng được; `perturb_question(text, mode, seed, case_id)` dùng rng riêng theo `"{seed}:{id}"` nên không phụ thuộc thứ tự câu. Không gây lỗi trên chữ có chữ số hoặc viết hoa toàn bộ (bộ sửa câu bắt giữ nguyên văn các chữ này; gây lỗi ở đó sẽ đo điều kiện 2 thay vì đo lỗi gõ chữ thường). Sửa lỗi phát hiện khi soát: đổi dấu thanh trên nguyên âm có mũ/móc ra ký tự tổ hợp sai (`viẻ̂n`) → đặt dấu mới cuối chuỗi dấu rồi NFC; thêm dấu thanh ưu tiên nguyên âm có mũ/móc.
  - `eval_retrieval.py`: `uses_llm_queries()` (gồm cờ sửa câu) dùng cho cảnh báo không lặp lại được và bỏ làm ấm cache embedding; `build_retrieval_fn(..., trace=None)` chế độ full gọi `rewriter.correct()` riêng, đo thời gian, ghi `trace["correction"]` rồi `rewrite(..., correction=...)`; `--perturb {none,strip_all,typo} --seed N` (mặc định seed `20261121`); case có `original_question`, `perturbations`, `correction`; `dataset.perturb` trong báo cáo.
  - `eval_confidence.py` (schema v2): cùng `--perturb/--seed`; `check_scope` lần hai trên câu đã sửa như `rag_chain` (`scope_stage`); `report.perturb`, `report.llm` (provider/model, không key); `summary.correction` = `correction_stats` theo bộ, theo category câu không có đáp án và theo loại lỗi (n, scope_pass, gate_pass, gate_pass_e2e, hit@4, corrected, reasons, số câu bị bỏ theo điều kiện 1/2/3, blocked_after_correction, thời gian median/p95/max trên mọi câu) + `changed_cases`; bảng in ra console.
  - Chạy 6 lần đo (cờ tắt/bật × có dấu/bỏ dấu/lỗi gõ) trên `ptit_rag_300` + `ptit_faq` + `ptit_no_answer_56`; báo cáo và bảng tổng hợp ở `documents/rag-eval/query-correction/` (số liệu ở V-06).
- File thay đổi: `backend/scripts/typo_variants.py` (mới), `backend/scripts/eval_retrieval.py`, `backend/scripts/eval_confidence.py`, `backend/tests/test_typo_variants.py` (mới), `backend/tests/test_eval_confidence.py`, `documents/rag-eval/query-correction/*` (mới).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác:
  - **Ngưỡng cuối: giữ `max(3, 20%)` và độ dài ≤ 2 lần.** Căn cứ: trên 1 128 lần gọi (3 bộ × 376 câu), chỉ 1 câu bị bỏ do điều kiện 1 và đó là câu LLM viết lại sai nghĩa; không câu sửa đúng nào bị bỏ, không câu nào bị bỏ do điều kiện 2/3. Không cần cờ `QUERY_CORRECTION_MAX_EDIT_RATIO`.
  - Câu viết lại nhỏ vẫn lọt ngưỡng (`Bậc Cao học` → `Bác sĩ cao học`, `Học viện` → `Học viên` ở câu bỏ dấu); không siết ngưỡng vì các lỗi này chỉ khác vài ký tự, siết sẽ bỏ cả câu sửa đúng. Ghi trong báo cáo, mục "Rủi ro quan sát được".
  - Không đo `ptit_no_answer_56` riêng: đã gộp vào cả 6 lần đo (có dấu, bỏ dấu, lỗi gõ).
- Kiểm tra đã chạy: `pytest tests/test_typo_variants.py tests/test_eval_confidence.py tests/test_eval_retrieval.py` đạt; 6 lần đo exit 0.
- Còn lại/blocker: không.

### S-05 — agent-rag

- Cập nhật lúc: `≤ 2026-11-21T16:09:08+07:00`.
- Đã làm: `README.md` (sơ đồ luồng có bước sửa câu và nhánh chặn câu đã sửa; bước 2; mục mới "Sửa chính tả câu hỏi bằng LLM"); MSG-agent-rag-004 (Chương 2), MSG-agent-rag-005 (Ngọc).
- File thay đổi: `README.md`, `implementation.md` của task.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: xem hai MSG.
- Kiểm tra đã chạy: đọc lại README (V-07).
- Còn lại/blocker: chờ phản hồi người phụ trách Chương 2 và Ngọc (không chặn đóng task).

## Trao đổi giữa agents

### MSG-agent-rag-001

- Lúc: `2026-11-21T12:28:50+07:00`.
- Từ: `agent-rag`; đến: coordinator (ghi nhận).
- Nhiệm vụ: toàn task.
- Loại: `decision`.
- Tham chiếu: MSG-agent-backend-002 (`.agents/tasks/2026-11-18-guardrail-unaccented-scope/implementation.md`).
- Nội dung: Người dùng quyết định xử lý câu không dấu bằng LLM khôi phục dấu thay vì khôi phục dấu theo luật hay chỉ mục BM25 không dấu, vì hệ thống chỉ phục vụ tiếng Việt. Thiết kế chốt: chỉ gọi LLM với câu không dấu; đầu ra chỉ được thêm dấu; kiểm `check_scope` cả câu gốc và câu khôi phục; dự phòng về câu gốc khi LLM lỗi.
- Hành động mong muốn: triển khai theo `plan.md`.

### MSG-agent-rag-002

- Lúc: `2026-11-21` (sau MSG-agent-rag-001).
- Từ: `agent-rag`; đến: coordinator (ghi nhận).
- Nhiệm vụ: S-01, S-04.
- Loại: `decision`.
- Tham chiếu: MSG-agent-rag-001.
- Nội dung: Người dùng quyết định không dùng luật phát hiện câu/chữ thiếu dấu ("không cần đánh dấu, LLM sẽ tự hiểu"). Khi cờ bật, mọi câu có chữ cái đều gửi LLM; LLM tự thêm dấu cho chữ còn thiếu, kể cả câu dấu một phần, và trả nguyên văn câu đủ dấu. Giữ kiểm tra đầu ra (bỏ dấu trùng câu gốc, chữ đã có dấu giữ nguyên) để LLM không đổi nghĩa hay chèn từ vào truy vấn. Đánh đổi: mọi câu thêm một lần gọi LLM — đo ở S-04 để chốt mặc định của cờ.
- Hành động mong muốn: triển khai S-01 theo `plan.md` đã cập nhật.

### MSG-agent-rag-003

- Lúc: `2026-11-21T13:02:24+07:00`.
- Từ: `agent-rag`; đến: coordinator (ghi nhận).
- Nhiệm vụ: toàn task.
- Loại: `decision`.
- Tham chiếu: MSG-agent-rag-002.
- Nội dung: Người dùng chỉ ra câu có thể gõ sai (typo, sai dấu thanh, sai dấu câu); bắt giữ nguyên chữ đã có dấu sẽ giữ luôn lỗi. Mở rộng thành sửa chính tả và dấu bằng LLM. Thay kiểm tra "bỏ dấu trùng khớp + giữ chữ có dấu" bằng: Levenshtein trên khóa bỏ dấu/bỏ dấu câu ≤ `max(3, 20%)`, giữ nguyên chữ có số/viết hoa, đầu ra một dòng ≤ 2 lần độ dài. Đổi ID task thành `2026-11-21-llm-query-correction` (thư mục cũ `2026-11-21-llm-accent-restoration` chưa commit, đã đổi tên), nhánh `feat/llm-query-correction`, cờ `QUERY_CORRECTION_ENABLED`, module `query_corrector.py`. S-04 thêm bộ sinh lỗi gõ.
- Hành động mong muốn: triển khai S-01 theo `plan.md` đã cập nhật.

### MSG-agent-rag-004

- Lúc: `≤ 2026-11-21T16:09:08+07:00`.
- Từ: `agent-rag`; đến: người phụ trách Chương 2.
- Nhiệm vụ: S-05.
- Loại: `proposal`.
- Tham chiếu: `documents/chuong-2/chuan-bi-bao-ve.md` Q-2, Q-3; thiết kế 2.7.1; `documents/rag-eval/query-correction/README.md`.
- Nội dung: Thiết kế 2.7.1 và câu trả lời Q-3 ghi "Bộ chuẩn hóa không gọi Dịch vụ LLM". Task này thêm bước sửa chính tả/dấu bằng LLM trước bộ chuẩn hóa theo luật, sau cờ `QUERY_CORRECTION_ENABLED` (mặc định chưa chốt, hiện `false`). Khi bật: (1) mọi câu được gửi LLM một lần với prompt chỉ sửa lỗi gõ; (2) đầu ra chỉ được dùng khi khoảng cách chỉnh sửa trên khóa bỏ dấu ≤ max(3, 20%), giữ nguyên chữ có số/viết hoa, một dòng, ≤ 2 lần độ dài; (3) Bộ kiểm soát (`check_scope`) xét **cả câu gốc và câu đã sửa** trước truy xuất; (4) câu trả lời vẫn sinh từ câu gốc; (5) LLM lỗi thì dùng câu gốc. Số đo: câu bỏ dấu qua gate 0 → 281/300, hit@4 40 → 245/300; câu lỗi gõ 144 → 283, 211 → 248; câu có dấu không đổi (0/376 câu bị sửa); `out_of_domain` vẫn từ chối 14/14. Đề xuất câu chữ (người phụ trách tự quyết, tôi không sửa `documents/chuong-2/`):
  - 2.7.1: "Bộ chuẩn hóa chạy theo luật, không gọi Dịch vụ LLM. Tùy chọn, trước Bộ chuẩn hóa, câu hỏi có thể được Dịch vụ LLM sửa chính tả và dấu; đầu ra bị giới hạn khoảng cách chỉnh sửa so với câu gốc và phải qua Bộ kiểm soát lần nữa."
  - Q-3: thêm "Khi bật bước sửa chính tả bằng LLM, Bộ kiểm soát xét cả câu gốc và câu đã sửa; câu đã sửa chỉ dùng để truy xuất, câu trả lời vẫn sinh từ câu gốc."
- Hành động mong muốn: xem xét, cập nhật Chương 2 nếu đồng ý; phản hồi trong mục trao đổi của task.

### MSG-agent-rag-005

- Lúc: `≤ 2026-11-21T16:09:08+07:00`.
- Từ: `agent-rag`; đến: Ngọc (FE).
- Nhiệm vụ: S-02, S-03.
- Loại: `contract`.
- Tham chiếu: `plan.md` mục "Hợp đồng dùng chung".
- Nội dung:
  - Cấu hình: `GET /api/config` → `retrieval.query_correction_enabled: bool`; `PUT /api/config` nhận `{"retrieval": {"query_correction_enabled": true|false|null}}` (`null`/bỏ khóa = giữ nguyên), lưu qua `app_config_overrides` như `query_rewrite_use_llm`. Gợi ý nhãn: "Sửa chính tả câu hỏi bằng LLM", mô tả "Mọi câu hỏi thêm một lần gọi LLM (median ~0,5 s, có lúc > 10 s)".
  - Stream: event `step` `query_rewrite` có thêm `detail.query_corrected: bool`, `detail.corrected_query: str` (rỗng nếu không sửa), `detail.correction_reason: str`; `retrieval_debug` có cùng ba khóa. Không đổi/bỏ khóa cũ. ReasoningPanel có thể hiện "Đã sửa: …" khi `query_corrected` (không bắt buộc).
  - Khi câu đã sửa bị guardrail chặn: không có event `guardrail` thứ hai; event `query_rewrite` vẫn phát với `rewritten_query` rỗng, sau đó câu từ chối như câu gốc bị chặn; `retrieval_debug.guardrail = {"allowed": false, "reason": ..., "stage": "corrected"}`.
  - Cache câu trả lời (CN13): khóa nên tính trên câu sau sửa + rewrite, không chỉ câu gốc.
- Hành động mong muốn: thêm công tắc trên màn Cấu hình khi tiện; báo lại nếu cần đổi hợp đồng.

## Bàn giao

- Lúc: `≤ 2026-11-21T16:09:08+07:00`; từ `agent-rag` (triển khai) cho coordinator/reviewer (`agent-rag`, `self_review`) và người dùng.
- Đã làm: S-01 … S-05 (chi tiết ở trên).
- File: xem từng nhiệm vụ; commit ghi ở mục "Commit" bên dưới.
- Giao diện ảnh hưởng: API cấu hình (`retrieval.query_correction_enabled`), trường mới của event `query_rewrite` và `retrieval_debug`, rewriter tùy biến của `RagChain` phải có `correct()` và nhận `correction=`.
- Kiểm tra: V-01 … V-08 (`verification.md`); pytest toàn bộ `1496 passed, 24 skipped`.
- Chưa xong: người dùng chốt giá trị mặc định của cờ (AC-05). Chưa push và chưa mở PR.
- Bước tiếp theo: người dùng chốt mặc định; review; push nhánh và mở PR vào `dev` khi người dùng đồng ý.

### Commit

- `9f2bdff` feat: correct question spelling and diacritics with LLM before retrieval (S-01, S-02, S-03, README, `.env.example`).
- `1c8c292` feat: measure query correction on unaccented and typo question variants (S-04 script + test).
- `3d7d17a` chore: add query correction eval reports (S-04 báo cáo).
- Commit kế tiếp: file task (`.agents/tasks/2026-11-21-llm-query-correction/`).

# Review: 2026-11-21-llm-query-correction

- Reviewer: `agent-rag`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved` cho phần mã và số đo trên bản được review; task chưa `done` vì AC-05 còn chờ người dùng chốt giá trị mặc định của cờ (không phải nhận xét review).
- Bản được review: working tree nhánh `feat/llm-query-correction` (nền `f3d01bd`) sau khi sửa R-01, R-02; trùng nội dung commit `9f2bdff`, `1c8c292`, `3d7d17a`.
- Cập nhật lúc: `2026-11-21T16:35:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 … AC-08; S-01 … S-05.
- File/thay đổi đã đọc: toàn bộ diff so với `f3d01bd`: `query_corrector.py`, `query_rewriter.py`, `rag_chain.py`, `config.py`, `config_store.py`, `schemas.py`, `eval_retrieval.py`, `eval_confidence.py`, `typo_variants.py`, các test mới/sửa, `README.md`, `.env.example`, `documents/rag-eval/query-correction/README.md`.
- Bằng chứng kiểm chứng: V-01 … V-08 trong `verification.md`; 6 báo cáo JSON.
- Điểm đã đánh giá: câu đúng không bị sửa hỏng; kiểm tra đầu ra nhận câu sửa lỗi gõ nhưng bỏ câu viết lại/chỉ dẫn; ngưỡng có căn cứ số liệu; `check_scope` lần hai; dự phòng khi LLM lỗi/hết budget; tương thích ngược của event stream và API cấu hình; độ trễ.

## Nhận xét

### R-01 — Thuộc tính không dùng

- Vị trí: `backend/app/generation/query_corrector.py`, `QueryCorrectionResult.called_llm`.
- Vấn đề: property không có nơi gọi.
- Tác động: mã thừa.
- Mức độ: `low`; bắt buộc: không.
- Người xử lý: `agent-rag`.
- Phản hồi: đã xóa; `pytest` toàn bộ đạt (`1496 passed, 24 skipped`).
- Trạng thái: `resolved`.

### R-02 — Hàm sinh biến thể lặp ở hai script

- Vị trí: `eval_confidence.perturb_cases` và `eval_retrieval.apply_perturbation`.
- Vấn đề: hai hàm giống hệt.
- Tác động: sửa một chỗ dễ quên chỗ kia.
- Mức độ: `low`; bắt buộc: không.
- Người xử lý: `agent-rag`.
- Phản hồi: `eval_confidence` dùng `apply_perturbation` import từ `eval_retrieval`; test đổi theo; `--from-report` và `--help` chạy được.
- Trạng thái: `resolved`.

### R-03 — Gợi ý tắt thinking có thể bị server OpenAI-compatible từ chối

- Vị trí: `query_corrector._no_thinking_kwargs`.
- Vấn đề: khóa `chat_template_kwargs` hợp với vLLM/SGLang (đã thử trên endpoint hiện tại). Server khắt khe với tham số lạ sẽ trả lỗi, khi đó mọi câu rơi về `llm_error` và chỉ có log mức info.
- Tác động: tính năng không có tác dụng nhưng không làm hỏng câu hỏi (dùng câu gốc).
- Mức độ: `medium`; bắt buộc: không (không đổi hành vi khi cờ tắt; dự phòng an toàn).
- Người xử lý: `agent-rag`.
- Phản hồi: ghi trong README và `implementation.md`. Hướng theo dõi: task riêng cho tùy chọn "tắt suy luận" ở tầng provider (cũng cần cho rewrite/multi-query bằng LLM với model thinking).
- Trạng thái: `deferred`.

### R-04 — LLM khôi phục dấu sai nghĩa mà vẫn trong ngưỡng

- Vị trí: hành vi của bước sửa câu; số liệu `on_strip_all.json`, `on_typo.json`.
- Vấn đề: 43/375 câu bỏ dấu được sửa khác câu gốc, có câu sai nghĩa (`Học viện` → `Học viên`, `chuyên ngành` → `chuyển ngành`, `Bậc Cao học` → `Bác sĩ cao học`). Kiểm tra đầu ra không phân biệt được vì chỉ khác dấu/vài ký tự.
- Tác động: truy xuất có thể lệch ở một số câu; câu trả lời vẫn sinh từ câu gốc. Tổng thể bản bỏ dấu vẫn đạt gate 281/300, hit@4 245/300.
- Mức độ: `medium`; bắt buộc: không (rủi ro đã nêu trong `plan.md`, đã đo và ghi lại).
- Người xử lý: `agent-rag`.
- Phản hồi: ghi ở báo cáo mục "Rủi ro quan sát được". Hướng theo dõi: thêm thuật ngữ miền (Học viện, chuyên ngành…) vào prompt hoặc chỉ mục BM25 không dấu làm lớp dự phòng (đã nêu ngoài phạm vi trong `task.md`).
- Trạng thái: `deferred`.

### R-05 — Đuôi độ trễ dài

- Vị trí: V-06.
- Vấn đề: median ~0,45 s nhưng p95 ~12 s mỗi câu với endpoint hiện tại (429 và phản hồi chậm). Bước này chịu `optional_step` (tối đa nửa thời gian còn lại của lượt), nên không làm lượt chat quá deadline nhưng có thể làm người dùng chờ lâu hơn.
- Tác động: trải nghiệm khi bật cờ.
- Mức độ: `low`; bắt buộc: không.
- Người xử lý: người dùng (chốt giá trị mặc định, AC-05).
- Phản hồi: số liệu đã đưa vào đề xuất chốt mặc định.
- Trạng thái: `deferred` (chờ quyết định của người dùng).

### R-06 — Hợp đồng rewriter tùy biến của `RagChain` thay đổi

- Vị trí: `rag_chain.iter_retrieve_context` gọi `query_rewriter.correct()` và `rewrite(..., correction=...)`.
- Vấn đề: rewriter tùy biến chỉ có `rewrite(question, history, budget)` sẽ lỗi.
- Tác động: chỉ 3 rewriter giả trong test, đã cập nhật (kế thừa `VietnameseQueryRewriter`). Không có nơi khác trong repo.
- Mức độ: `low`; bắt buộc: không.
- Người xử lý: `agent-rag`.
- Phản hồi: ghi trong `implementation.md` S-03.
- Trạng thái: `resolved`.

## Đánh giá chung

- Cờ tắt: `correct()` trả `disabled` trước mọi lời gọi LLM; `rewrite()` cho kết quả giống `rule_based_rewrite` trên 376 câu fixture (test), số đo cờ tắt trùng số nền của task trước (284/249). Event stream chỉ thêm khóa.
- `check_scope` lần hai chạy ở mọi nhánh có câu đã sửa khi guardrail bật, trước rewrite/truy xuất; nhánh bị chặn không truy xuất, không gọi LLM trả lời.
- Ngưỡng kiểm tra đầu ra có căn cứ số liệu: 1 câu bị bỏ trên 1 128 lần gọi và đó là câu viết lại sai.
- Bộ sinh lỗi gõ có test và seed cố định; báo cáo ghi model, ngưỡng, cờ, fingerprint corpus.

## Lịch sử các vòng review

- Vòng 1 (`2026-11-21T16:30:00+07:00`): R-01 … R-06; sửa R-01, R-02; chạy lại pytest toàn bộ đạt; R-03 … R-05 hoãn có lý do; R-06 ghi nhận.

## Kết luận

- Kết luận: `approved` (self_review) trên bản sau khi sửa R-01, R-02.
- Nhận xét bắt buộc còn mở: không.
- Nhận xét hoãn lại: R-03, R-04 (task theo dõi đề xuất ở trên), R-05 (người dùng chốt mặc định).
- Phần chưa review / giới hạn: chưa có review độc lập; chưa thử provider khác ngoài `openai_compatible`; không review FE.
- Bước tiếp theo: người dùng chốt giá trị mặc định của `QUERY_CORRECTION_ENABLED`; push và mở PR vào `dev` khi người dùng đồng ý.

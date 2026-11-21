# Review: 2026-11-21-llm-query-correction

- Reviewer: `agent-rag`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập). Vòng 2 chạy ở phiên mới, không dùng lịch sử chat của phiên triển khai, nhưng vẫn là `agent-rag` nên vẫn ghi `self_review`.
- Trạng thái: `approved` cho phần mã và số đo trên bản được review; task chưa `done` vì AC-05 còn chờ người dùng chốt giá trị mặc định của cờ (không phải nhận xét review).
- Bản được review: vòng 1: working tree nhánh `feat/llm-query-correction` (nền `f3d01bd`) sau khi sửa R-01, R-02; trùng nội dung commit `9f2bdff`, `1c8c292`, `3d7d17a`. Vòng 2: commit `d24f482` (working tree sạch). Vòng 3: working tree sau `d24f482` có bản sửa R-07, R-08, R-09 (chưa commit).
- Cập nhật lúc: `2026-11-21T16:44:32+07:00` (vòng 3).

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

### R-07 — Bỏ ngoặc kép bao ngoài làm câu LLM trả nguyên văn bị tính là "đã sửa"

- Vị trí: `backend/app/generation/query_corrector.py`, `_clean_output` và `validate_correction` (so `_same_text(question, cleaned)`).
- Vấn đề: `_clean_output` luôn bỏ ngoặc kép/backtick bao ngoài, kể cả khi chính người dùng gõ câu có ngoặc. Thử: `validate_correction('"hoc phi la bao nhieu"', '"hoc phi la bao nhieu"')` → `corrected=True`, `reason=corrected`, `text='hoc phi la bao nhieu'`, dù LLM trả nguyên văn.
- Tác động: với câu có ngoặc bao ngoài, cờ bật + LLM trả nguyên văn không còn cho kết quả rewrite giống hệt cờ tắt (yêu cầu AC-04; test fixture vẫn đạt vì không câu fixture nào có ngoặc bao ngoài). Câu bị kiểm `check_scope` lần hai và bị đếm vào `corrected` không cần thiết. Truy xuất gần như không đổi vì BM25/vector bỏ qua ngoặc.
- Mức độ: `low`; bắt buộc: không.
- Người xử lý: `agent-rag`.
- Đề xuất: chỉ bỏ ngoặc bao ngoài khi câu gốc không có ngoặc đó (hoặc so `_same_text` với đầu ra trước khi bỏ ngoặc); thêm một ca vào test.
- Phản hồi: `_clean_output(output, question)` chỉ bỏ ngoặc bao ngoài (`"`, `'`, `` ` ``, `“…”`) khi câu gốc không có cùng cặp ngoặc đó. Test `test_user_quoted_question_echoed_is_unchanged` (3 ca → `unchanged`), `test_user_quoted_question_keeps_its_quotes_when_corrected`. Xác nhận: V-02 chạy lại, V-08 lần 3 (`1507 passed, 24 skipped`).
- Trạng thái: `resolved`.

### R-08 — Nhãn mở đầu ("Câu đã sửa: …") lọt điều kiện 1 ở câu dài

- Vị trí: `validate_correction`, điều kiện 1.
- Vấn đề: ngưỡng 20% độ dài khóa cho phép thêm khoảng 8–10 ký tự ở câu có khóa ≥ 40–50 ký tự. Thử: câu 85 ký tự, đầu ra `Câu đã sửa: <câu gốc có dấu>` → `corrected`. Model khác `qwen3.8-27b` (OpenAI, Gemini, model nhỏ) hay thêm nhãn như vậy dù prompt cấm; số đo V-06 chỉ có một model và không gặp trường hợp này.
- Tác động: truy vấn truy xuất có thêm từ rác (`câu`, `sửa`), làm loãng BM25 một chút; câu trả lời vẫn sinh từ câu gốc, `check_scope` lần hai vẫn chạy. Không ảnh hưởng an toàn.
- Mức độ: `low`; bắt buộc: không.
- Người xử lý: `agent-rag`.
- Đề xuất: bỏ một số nhãn mở đầu phổ biến (`Câu đã sửa:`, `Đã sửa:`, `Corrected:`) trong `_clean_output`, hoặc ghi rõ giới hạn này cùng R-03 khi đổi provider; đo lại V-06 nếu đổi model.
- Phản hồi: `_LABEL_PREFIX_RE` bỏ nhãn mở đầu (`Câu đã sửa:`, `câu hỏi được sửa lại:`, `Đã sửa:`, `Sửa lại:`, `Kết quả:`, `Corrected question/query/text:`, `Output:`, không phân biệt hoa thường, cả `：`) trước kiểm tra, trừ khi câu gốc bắt đầu bằng nhãn đó; thứ tự ngoặc → nhãn → ngoặc nên `"Kết quả: …"` và `Đã sửa: “…”` cũng được làm sạch. Test `test_label_prefix_is_removed_from_output` (6 ca), `test_label_prefix_kept_when_question_starts_with_it`. Chạy kiểm tra mới trên 1 121 đầu ra LLM thật đã lưu: 0 quyết định thay đổi, số đo V-06 vẫn đúng. Vẫn chưa đo model khác (giới hạn ghi ở R-03).
- Trạng thái: `resolved`.

### R-09 — Timestamp trong file task muộn hơn commit chứa chúng

- Vị trí: `task.md` (cập nhật `16:40`), `implementation.md` (S-04/S-05 `16:15`, bàn giao `16:20`), `verification.md` (V-07 `16:15`, V-08 lần 2 `16:20`), `review.md` vòng 1 (`16:30`, `16:35`).
- Vấn đề: các file này nằm trong commit `d24f482` lúc `2026-11-21T16:09:08+07:00`, nên các mốc sau `16:09` không thể là thời điểm thật. Quy ước `.agents/README.md` cấm bịa timestamp. Timestamp trong báo cáo đo (`created_at` 15:20 → 16:02) khớp V-06, không bị ảnh hưởng.
- Tác động: nhật ký phối hợp sai thứ tự thời gian; không ảnh hưởng mã hay số đo.
- Mức độ: `low`; bắt buộc: không.
- Người xử lý: `agent-rag` (coordinator).
- Đề xuất: sửa các mốc này thành thời điểm thật (≤ `16:09:08`) hoặc ghi "khoảng", trong lần cập nhật task tới.
- Phản hồi: thời điểm thật của các mục này không được ghi lại; chỉ biết chúng nằm sau báo cáo đo cuối (`on_typo.json`, 16:02:20, vì có trích số liệu V-06) và trước commit `d24f482` (16:09:08). Đã đổi 10 mốc trong `task.md`, `implementation.md`, `verification.md`, `review.md` thành cận trên `≤ 2026-11-21T16:09:08+07:00` thay vì đoán phút (mốc "Cập nhật lúc" 16:35 của vòng 1 đã được thay khi ghi vòng 2; "Cập nhật lúc" của `task.md` nay là thời điểm thật của lần sửa này); ghi lý do trong lịch sử quyết định của `task.md`. Không còn mốc nào sau 16:09:08 ngoài các mục vòng 2/3.
- Trạng thái: `resolved`.

## Đánh giá chung

- Cờ tắt: `correct()` trả `disabled` trước mọi lời gọi LLM; `rewrite()` cho kết quả giống `rule_based_rewrite` trên 376 câu fixture (test), số đo cờ tắt trùng số nền của task trước (284/249). Event stream chỉ thêm khóa.
- `check_scope` lần hai chạy ở mọi nhánh có câu đã sửa khi guardrail bật, trước rewrite/truy xuất; nhánh bị chặn không truy xuất, không gọi LLM trả lời.
- Ngưỡng kiểm tra đầu ra có căn cứ số liệu: 1 câu bị bỏ trên 1 128 lần gọi và đó là câu viết lại sai.
- Bộ sinh lỗi gõ có test và seed cố định; báo cáo ghi model, ngưỡng, cờ, fingerprint corpus.

## Lịch sử các vòng review

- Vòng 1 (`≤ 2026-11-21T16:09:08+07:00`): R-01 … R-06; sửa R-01, R-02; chạy lại pytest toàn bộ đạt; R-03 … R-05 hoãn có lý do; R-06 ghi nhận.
- Vòng 2 (`2026-11-21T16:19:45+07:00`, commit `d24f482`): đọc lại toàn bộ diff `f3d01bd..d24f482` trong `backend/app`, `backend/scripts`, README, `.env.example`; đối chiếu năm file task.
  - Đã kiểm: thứ tự guardrail → sửa câu → guardrail lần hai → rewrite trong `rag_chain`; nhánh chặn ở cả `answer()` và route stream (`routes.py`, `guardrail_allowed`) trả `OUT_OF_SCOPE_ANSWER`; câu trả lời sinh từ `request.message`/`question` gốc; lỗi không tạm thời (vd. 400 khi server từ chối `chat_template_kwargs`) không đặt `budget.degraded`, nên không làm các bước LLM sau bỏ qua; `levenshtein` dừng sớm đúng (min của hàng không giảm), câu tối đa 2 000 ký tự tốn ≤ ~0,5 s; seed chuỗi của `random.Random` không phụ thuộc `PYTHONHASHSEED`; không sửa fixture, không sửa `documents/chuong-2/`.
  - Chạy: `pytest tests/test_query_corrector.py tests/test_query_rewriter.py tests/test_rag_chain.py tests/test_typo_variants.py tests/test_eval_confidence.py tests/test_eval_retrieval.py tests/test_config_api.py tests/test_config_persistence.py` → `190 passed, 1 warning` (warning Starlette có sẵn). Không chạy lại pytest toàn bộ (cần Postgres) và không chạy lại đo LLM.
  - Đối chiếu số liệu: `summary.correction.by_dataset.ptit_rag_300` của 6 báo cáo khớp bảng V-06 (gate 284/284, 0→281, 144→283; hit@4 249/249, 40→245, 211→248; `llm_error` 7; `too_different` 1; median/p95 452/9 982, 460/13 042, 453/12 087 ms).
  - Nhận xét mới: R-07, R-08, R-09 (đều `low`, không bắt buộc).
  - Lưu ý cho quyết định AC-05: số đo thời gian chạy không có budget lượt (`correct(query)` với `budget=None`). Trong app, bước sửa câu được tối đa nửa thời gian còn lại (`optional_step`, mặc định ≈ 30 s trên deadline 60 s), nên đuôi chậm/429 trong thực tế bị cắt và rơi về câu gốc thay vì đợi.
- Vòng 3 (`2026-11-21T16:44:32+07:00`): theo yêu cầu người dùng, `agent-rag` sửa R-07, R-08, R-09. Reviewer đọc lại diff `query_corrector.py` (`_clean_output`, `_strip_added_quotes`, `_LABEL_PREFIX_RE`) và 11 test mới; đối chiếu V-02 (chạy lại, `91 passed` trên 3 file), V-08 lần 3 (`1507 passed, 24 skipped`) và lần chạy lại kiểm tra đầu ra trên 1 121 đầu ra LLM thật (0 khác biệt). R-07, R-08, R-09 → `resolved`.

## Kết luận

- Kết luận: `approved` (self_review) trên bản sau khi sửa R-01, R-02; vòng 2 giữ `approved` trên commit `d24f482`; vòng 3 `approved` trên working tree có bản sửa R-07, R-08, R-09.
- Nhận xét bắt buộc còn mở: không.
- Nhận xét không bắt buộc còn mở: không (R-07, R-08, R-09 đã `resolved` ở vòng 3).
- Nhận xét hoãn lại: R-03, R-04 (task theo dõi đề xuất ở trên), R-05 (người dùng chốt mặc định).
- Phần chưa review / giới hạn: chưa có review độc lập; chưa thử provider khác ngoài `openai_compatible`; không review FE.
- Bước tiếp theo: người dùng chốt giá trị mặc định của `QUERY_CORRECTION_ENABLED`; push và mở PR vào `dev` khi người dùng đồng ý.

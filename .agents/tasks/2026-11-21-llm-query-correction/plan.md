# Plan: 2026-11-21-llm-query-correction

## Phân công

### S-01 — Bộ sửa câu bằng LLM

- Agent: `agent-rag`
- Trạng thái: `done`
- Mục tiêu: lớp `QueryCorrector` với `correct(question, budget=None) -> QueryCorrectionResult` (`text`, `corrected: bool`, `reason`); phục vụ `AC-01`, `AC-02`.
  - S-01.1: Điều kiện gọi LLM: cờ bật, câu có ít nhất một chữ cái, LLM đã cấu hình, `budget.optional_step()` không trả `None`. Không có luật phát hiện câu sai: mọi câu đều gửi LLM.
  - S-01.2: Prompt hẹp (xem Ràng buộc trong `task.md`): chỉ sửa chính tả, dấu thanh, dấu câu, lỗi gõ Telex/VNI, dính/tách chữ; câu đúng trả nguyên văn; không diễn đạt lại, không mở rộng viết tắt, không trả lời; giữ số, mã môn, tên riêng; câu hỏi là dữ liệu. Có vài ví dụ ngắn (few-shot) gồm cả câu đúng giữ nguyên. `temperature=0`, `max_tokens` theo độ dài câu.
  - S-01.3: Kiểm tra đầu ra: `key(s)` = NFC → viết thường → `strip_accents` → bỏ ký tự không phải chữ/số. Nhận khi (1) Levenshtein(`key(in)`, `key(out)`) ≤ `max(3, 0.2 * len(key(in)))`; (2) chữ có chữ số hoặc viết hoa toàn bộ ≥ 2 ký tự trong câu gốc còn nguyên văn; (3) đầu ra một dòng, khác rỗng, ≤ 2 lần độ dài câu gốc. `reason`: `corrected`, `unchanged`, `too_different`, `protected_token_changed`, `invalid_output`, `llm_error`, `skipped_no_letters`, `skipped_budget`, `disabled`, `not_configured`. Levenshtein tự viết (chuỗi ngắn), không thêm dependency.
  - S-01.4: Mọi lỗi LLM → trả câu gốc, ghi log mức info như `query_rewriter`.
- Phạm vi file được sửa: `backend/app/generation/query_corrector.py` (mới), `backend/app/generation/prompts.py` (nếu đặt prompt ở đây), `backend/tests/test_query_corrector.py` (mới).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: module + test; ghi các `reason` và ngưỡng trong `implementation.md`.
- Người nhận: `agent-rag`.

### S-02 — Cờ cấu hình

- Agent: `agent-rag`
- Trạng thái: `done`
- Mục tiêu: `query_correction_enabled` (`QUERY_CORRECTION_ENABLED`) trong `Settings`, xuất/nhận trong nhóm `retrieval` của API cấu hình, lưu qua `app_config_overrides`; phục vụ `AC-05`. Có thể thêm `QUERY_CORRECTION_MAX_EDIT_RATIO` (mặc định 0.2) nếu S-04 cần chỉnh ngưỡng mà không sửa mã — quyết định ghi trong `implementation.md`.
- Phạm vi file được sửa: `backend/app/core/config.py`, `backend/app/api/schemas.py`, `backend/tests/test_config_api.py`, `backend/tests/test_config_persistence.py`.
- Phụ thuộc: không có (cùng agent nên làm tuần tự với S-01).
- Đầu ra/bàn giao: cờ + test; hợp đồng cấu hình cho Ngọc (MSG).
- Người nhận: `agent-rag`; Ngọc (công tắc FE).

### S-03 — Tích hợp vào rewrite và rag_chain

- Agent: `agent-rag`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-03`, `AC-04`.
  - `VietnameseQueryRewriter.rewrite()` gọi `QueryCorrector` trên câu gốc **trước** `rule_based_rewrite`, để lời dẫn có dấu và từ điển viết tắt khớp được trên câu đã sửa. Giữ chữ ký `rewrite()` trả `str` cho nơi gọi cũ; thêm phương thức hoặc thuộc tính để rag_chain lấy kết quả sửa câu — chốt trong `implementation.md`.
  - `rag_chain.iter_retrieve_context`: guardrail bật và câu đã được sửa → `check_scope(corrected_text)`; bị chặn → trả kết quả chặn như nhánh hiện có.
  - Sự kiện `query_rewrite` thêm `query_corrected`, `corrected_query`; `retrieval_debug` thêm cùng trường.
  - Câu trả lời vẫn sinh từ `question` gốc.
- Phạm vi file được sửa: `backend/app/generation/query_rewriter.py`, `backend/app/generation/rag_chain.py`, `backend/tests/test_query_rewriter.py`, `backend/tests/test_rag_chain.py`.
- Phụ thuộc: S-01, S-02.
- Đầu ra/bàn giao: tích hợp + test; mô tả trường mới của sự kiện stream cho Ngọc (FE ReasoningPanel có thể hiển thị câu đã sửa — không bắt buộc).
- Người nhận: `agent-rag`.

### S-04 — Bộ câu lỗi gõ, script đo và số liệu

- Agent: `agent-rag`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-04`, `AC-06`.
  - Bộ sinh biến thể lỗi (hàm thuần, có test, seed cố định): `strip_all` (bỏ hết dấu), `strip_partial` (bỏ dấu một tỷ lệ chữ), `wrong_tone` (đổi dấu thanh), `telex_leftover` (`học` → `hocj`, `phí` → `phis`, `nhiêu` → `nhieeu`), `char_noise` (thêm/bớt/đổi chỗ một ký tự), `merge_words` (dính hai chữ), `drop_punct` (bỏ dấu câu). Bộ lỗi gõ: mỗi câu 1–3 lỗi trộn, ghi loại lỗi theo câu.
  - `eval_retrieval.py`/`eval_confidence.py`: tùy chọn `--perturb {none,strip_all,typo} --seed N` (sinh lúc chạy, không ghi fixture mới); cảnh báo không lặp lại được và không làm ấm cache embedding trước khi cờ sửa câu bật; báo cáo thêm số câu sửa, số câu bị bỏ theo `reason`, thời gian sửa câu (median, p95), kết quả theo loại lỗi.
  - Chạy đo, mỗi bộ với cờ tắt và cờ bật: `ptit_rag_300` có dấu / bỏ dấu / lỗi gõ; `ptit_no_answer_56` có dấu và lỗi gõ. Bản có dấu cờ bật: liệt kê câu bị LLM sửa. Nếu nhiều câu sửa đúng bị bỏ vì `too_different` hoặc câu viết lại lọt qua, chỉnh ngưỡng và chạy lại; ghi các lần chạy.
  - Lưu báo cáo `documents/rag-eval/query-correction/`.
- Phạm vi file được sửa: `backend/scripts/eval_retrieval.py`, `backend/scripts/eval_confidence.py`, module/script sinh lỗi gõ trong `backend/scripts/` (tên chốt khi làm), test tương ứng trong `backend/tests/`, `documents/rag-eval/query-correction/*`.
- Phụ thuộc: S-03; Postgres (Docker) chạy, API key LLM + embedding.
- Đầu ra/bàn giao: báo cáo JSON + bảng trong `verification.md`.
- Người nhận: verifier.

### S-05 — Tài liệu và thông báo

- Agent: `agent-rag`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-07`.
  - Cập nhật `README.md`.
  - MSG cho người phụ trách Chương 2: thiết kế 2.7.1 và câu trả lời Q-3 ghi "Bộ chuẩn hóa không gọi Dịch vụ LLM"; nay bước chuẩn hóa gọi LLM để sửa chính tả và dấu, đã kiểm `check_scope` cả câu gốc và câu đã sửa, đầu ra bị giới hạn khoảng cách chỉnh sửa. Kèm số liệu S-04 và đề xuất câu chữ sửa (không tự sửa `documents/chuong-2/`).
  - MSG cho Ngọc: cờ `query_correction_enabled` trong nhóm `retrieval` của API cấu hình; trường mới trong sự kiện `query_rewrite`. Lưu ý cho cache (CN13): khóa cache nên tính trên câu sau sửa + rewrite.
- Phạm vi file được sửa: `README.md`, `implementation.md` của task.
- Phụ thuộc: S-04 (để có số liệu).
- Người nhận: người phụ trách Chương 2; Ngọc.

## Hợp đồng dùng chung

- Cấu hình: `GET/PUT` cấu hình runtime, nhóm `retrieval`, khóa `query_correction_enabled: bool` (PUT nhận `bool | None`, `None` = giữ nguyên) — cùng kiểu với `query_rewrite_use_llm`. Bên cung cấp: `agent-rag`; bên dùng: FE màn Cấu hình (Ngọc).
- Sự kiện stream `query_rewrite`: `detail` giữ `rewritten_query`, thêm `query_corrected: bool`, `corrected_query: str` (rỗng nếu không sửa), `correction_reason: str`. `retrieval_debug` thêm cùng các khóa. Thêm khóa, không đổi/bỏ khóa cũ.
- Khi câu đã sửa bị chặn: không phát sự kiện `guardrail` thứ hai; dùng `retrieval_debug.guardrail = {"allowed": false, "reason": <reason>, "stage": "corrected"}`. Chốt lại trong `implementation.md` nếu đổi.
- File mã nguồn dùng chung và người sửa: tất cả do `agent-rag` sửa. `backend/app/core/config.py`, `backend/app/api/schemas.py` là file chung với Ngọc — chỉ thêm trường, báo Ngọc trước khi commit nếu Ngọc đang có nhánh sửa cùng file.
- Lượt ghi năm file task: `agent-rag` ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `agent-rag`; phạm vi kiểm chứng: AC-01 … AC-08.
- Reviewer: `agent-rag` hoặc agent review khác do người dùng chỉ định; phạm vi review: S-01 … S-05, toàn bộ diff nhánh.
- Hình thức review: `self_review` (đổi thành `independent` nếu có reviewer khác).
- Người xử lý nhận xét: `agent-rag`; reviewer xác nhận sau khi sửa.

## Thứ tự tích hợp và kiểm chứng

1. S-02 (cờ) và S-01 (bộ sửa câu), tuần tự trong cùng nhánh.
2. S-03 tích hợp vào `query_rewriter` và `rag_chain`; chạy `pytest` backend.
3. S-04 bộ sinh lỗi gõ, sửa script, bật Docker Postgres, chạy đo, chỉnh ngưỡng; ghi `verification.md`.
4. S-05 cập nhật README, gửi MSG cho người phụ trách Chương 2 và Ngọc.
5. Review trên bản mới nhất; sửa nhận xét bắt buộc, kiểm tra lại; coordinator đóng task và mở PR vào `dev`.

## Rủi ro và điều chỉnh kế hoạch

- Lệch thiết kế Chương 2 (2.7.1, Q-3): hội đồng có thể hỏi. Xử lý: kiểm `check_scope` hai lần, giới hạn khoảng cách chỉnh sửa, gửi đề xuất sửa cho người phụ trách Chương 2 (S-05).
- Tăng độ trễ và chi phí: khi cờ bật, **mọi câu** (cả câu đúng) thêm một lần gọi LLM. Đo median/p95 ở S-04; budget `optional_step` giới hạn thời gian; người dùng chốt giá trị mặc định của cờ theo số đo.
- LLM "sửa" câu đúng thành sai (`sinh` → `sính`, `thi` → `thì` khi ý là `thi`, đổi thuật ngữ): kiểm tra đầu ra không chặn được vì thay đổi nhỏ. Đo số câu đúng bị sửa và ảnh hưởng tới gate/hit@4 ở S-04 (AC-04); prompt có ví dụ câu đúng giữ nguyên.
- Ngưỡng khoảng cách: quá chặt thì bỏ câu sửa đúng có nhiều lỗi (Telex sót nhiều phím trong câu ngắn); quá lỏng thì câu viết lại ngắn có thể lọt (ví dụ mở rộng một từ viết tắt trong câu dài vẫn trong ngưỡng — chấp nhận được vì không đổi ý). Chỉnh theo phân bố `too_different` ở S-04.
- Chèn lệnh ngắn trong ngưỡng khoảng cách: vẫn qua `check_scope` lần hai; câu trả lời sinh từ câu gốc.
- LLM lỗi/hết budget: câu sai quay về hành vi cũ (bị gate từ chối). Ghi trong README; nếu tỷ lệ lỗi cao, đề xuất task chỉ mục BM25 không dấu làm lớp dự phòng.
- Kết quả không lặp lại hoàn toàn dù `temperature=0`: script đo cảnh báo; ghi model và thời điểm đo.
- Từ viết tắt không dấu (`dkhp`) không khớp `ABBREVIATIONS` (khóa `đkhp`) nếu LLM giữ nguyên: ngoài phạm vi, ghi lại cho mục mở rộng từ điển viết tắt.
- Câu nối tiếp ghép lịch sử có lỗi gõ: lịch sử không được sửa; ghi lại, ngoài phạm vi.

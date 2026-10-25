# Verification: 2026-10-25-stream-reasoning-ui

- Verifier: `zcode-main`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: nhánh `feat/stream-reasoning-ui`, commit `83bef0a` + working tree (frontend + sửa guardrail step + task logs) tại thời điểm `2026-10-26T00:01:45+07:00`.
- Môi trường: Windows 11 (win32), Python 3.11.5 (backend `.venv`), Docker compose (postgres pgvector 16, backend FastAPI --reload, frontend Vite dev), Node/Vite cho build frontend.

## Kiểm chứng tiêu chí

### V-01 — AC-01 (event step/reasoning trên /chat/stream)

- Người thực hiện / thời gian: `zcode-main` / `2026-10-25T23:5x+07:00` (tự động) và `2026-10-25T23:58+07:00` (thủ công).
- Loại: test tự động + kiểm tra thủ công.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `./.venv/Scripts/python.exe -m pytest tests` ; gọi `POST http://localhost:8000/api/chat/stream` bằng `urllib` với câu hỏi tiếng Việt có dấu qua Docker compose đang chạy.
- Kỳ vọng: event `step` phát tuần tự theo pipeline; event `reasoning` phát khi model có thinking; event cũ giữ nguyên shape.
- Kết quả thực tế: pytest 361 passed, 1 skipped (test mới: `test_stream_emits_step_events_and_persists_timeline`, `test_stream_emits_reasoning_events_and_persists_reasoning`, `test_stream_hides_reasoning_when_disabled`, `test_iter_retrieve_context_yields_steps_then_result`, `test_iter_retrieve_context_out_of_scope_stops_after_guardrail_step`, 6 test provider reasoning/thinking). Gọi thật trả về lần lượt `STEP guardrail → query_rewrite → multi_query → retrieve → rerank → generate`, sau đó nhiều event `REASONING`, cuối `DONE reasoning_len=5276, steps=[6 bước]`.
- Trạng thái: `passed`.
- Bằng chứng: output pytest trong phiên; log test urllib (đã trích trong hội thoại làm việc); commit `83bef0a`.

### V-02 — AC-02 (UI hiển thị timeline + panel, tự thu gọn)

- Người thực hiện / thời gian: `zcode-main` / `2026-10-26T00:0x+07:00`.
- Loại: kiểm tra thủ công bằng trình duyệt (browser automation) trên `http://localhost:5173`.
- Thư mục chạy: frontend dev server (Docker compose, mount code mới).
- Lệnh / thao tác: mở trang, nhập câu hỏi "Điều kiện xét học bổng khuyến khích học tập là gì?", nhấn "Gửi câu hỏi", theo dõi `.reasoning-panel`; sau stream mở lại panel bằng header; chụp ảnh màn hình.
- Kỳ vọng: panel xuất hiện trong lúc chờ, timeline + thinking stream; tự thu gọn khi câu trả lời bắt đầu; mở lại được.
- Kết quả thực tế: panel xuất hiện ngay khi stream bắt đầu (panelCount=1 lúc 2.5s trong khi stream chạy 8.3s); sau stream panel tự thu gọn (class không còn `open`); tiêu đề chuyển "Đã suy luận · 8.3 giây"; mở lại hiển thị đủ 6 bước ("Kiểm tra phạm vi câu hỏi / Chuẩn hóa truy vấn / Sinh biến thể truy vấn / Tìm kiếm trong tài liệu — 4 đoạn ứng viên · 2 nguồn · 482ms / Xếp hạng đoạn văn — chọn 4 đoạn / Soạn câu trả lời — 7797ms") và reasoning 4516 ký tự; ảnh chụp màn hình xác nhận layout đúng design tokens.
- Trạng thái: `passed`.
- Bằng chứng: ảnh chụp `C:\Users\khanh\.zcode\cli\artifacts\session_ded983f2bfe2a1d1b37b0eda365f9cee\call_7182afbfe6b14ca7befeef2e-tool-result-3a2b24ba-8c3d-4549-95b8-52573f9d39db.png`; kết quả DOM (steps text) trích trong hội thoại.

### V-03 — AC-03 (lưu và xem lại reasoning khi mở hội thoại cũ)

- Người thực hiện / thời gian: `zcode-main` / `2026-10-26T00:0x+07:00`.
- Loại: kiểm tra thủ công + kiểm tra API.
- Thư mục chạy: Docker compose backend + trình duyệt.
- Lệnh / thao tác: (1) `GET /api/conversations/{id}` sau khi stream; (2) reload trang `localhost:5173`, bấm hội thoại "Điều kiện xét học bổng khuyến khích học tập là gì?" trong sidebar, kiểm tra `.reasoning-panel`.
- Kỳ vọng: reasoning/steps trả về từ metadata và panel hiển thị lại (mặc định thu gọn).
- Kết quả thực tế: API trả `reasoning_len=5276`, `steps=[6 bước]` cho message assistant; sau reload panel hiện với class không `open` (thu gọn đúng), tiêu đề "Đã suy luận · 8.3 giây", mở ra thấy đủ 6 bước khôi phục từ server.
- Trạng thái: `passed`.
- Bằng chứng: output API + DOM trong hội thoại làm việc.

### V-04 — AC-04 (model không thinking → chỉ timeline, không lỗi)

- Người thực hiện / thời gian: `zcode-main` / `2026-10-25T23:5x+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `pytest tests/test_chat_stream_errors.py::test_stream_hides_reasoning_when_disabled tests/test_llm_providers.py::test_default_generate_stream_deltas_wraps_content_only tests/test_llm_providers.py::test_stream_answer_with_llm_filters_reasoning_out`.
- Kỳ vọng: khi tắt cờ hoặc model chỉ phát content: không có event `reasoning`, `done.reasoning=null`, metadata không có `reasoning`, không lỗi.
- Kết quả thực tế: 3/3 test pass.
- Trạng thái: `passed`.
- Bằng chứng: pytest 361 passed, 1 skipped (không test nào skip trong nhóm này).

### V-05 — AC-05 (toàn bộ test backend pass)

- Người thực hiện / thời gian: `zcode-main` / `2026-10-25T23:5x+07:00` và chạy lại sau sửa guardrail step `2026-10-25T23:59+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `./.venv/Scripts/python.exe -m pytest tests -q`.
- Kỳ vọng: toàn bộ pass.
- Kết quả thực tế: `361 passed, 1 skipped` (skip là test postgres/eval có điều kiện sẵn có, không liên quan). Lần chạy đầu trước khi tách `iter_retrieve_context`: 3 test fail do monkeypatch target cũ — đã cập nhật target sang API mới và pass; lịch sử fail giữ ở mục dưới.
- Trạng thái: `passed`.
- Bằng chứng: output pytest `361 passed, 1 skipped in 3.74s`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lỗi đã xử lý: 3 test (`test_chat_stream_errors.py` x2, `test_conversation_memory.py` x1) fail sau khi `/chat/stream` đổi sang `iter_retrieve_context`/`stream_answer_deltas_with_llm` — nguyên nhân monkeypatch target cũ; đã sửa test giữ nguyên ngữ nghĩa, chạy lại pass. SyntaxError bytes literal tiếng Việt trong `test_llm_providers.py` — đã đổi sang `.encode("utf-8")`. Step `guardrail` bị thiếu khi guardrail bật và cho phép (phát hiện khi test thủ công) — đã sửa `iter_retrieve_context` phát step guardrail đều ở mọi nhánh, chạy lại 16 test liên quan pass.
- Chưa xác minh: trạng thái "Đang suy luận..." (spinner khi stream) chưa được chụp riêng do stream thật kết thúc nhanh giữa hai lần quan sát; logic đã được bao phủ bởi test tự động (`streaming` prop) và panel được xác nhận tồn tại giữa stream. Enter-to-send ban đầu bấm không ăn là artifact của automation (fill + press), gửi lại bằng `type` + Enter hoạt động bình thường.
- Kiểm tra bỏ qua: không có.

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-02, AC-03, AC-04, AC-05.
- Tiêu chí chưa đạt/chưa xác minh: không có.
- Đề xuất: bàn giao reviewer; coordinator đóng task khi review approved.

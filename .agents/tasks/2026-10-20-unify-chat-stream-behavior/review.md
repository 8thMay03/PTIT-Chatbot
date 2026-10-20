# Review: 2026-10-20-unify-chat-stream-behavior

- Reviewer: `agent-glm-5-3-flash`.
- Hình thức: `self_review` (một agent duy nhất trong phiên; không mô tả là review độc lập).
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `fix/chat-stream-consistency` (diff so với `dev` tại `54a5582`), gồm `backend/app/llm/base.py`, `backend/app/llm/__init__.py`, `backend/app/generation/llm.py`, `backend/app/api/routes.py`, `backend/tests/test_llm_providers.py`, `backend/tests/test_chat_stream_errors.py` (mới), `frontend/src/ChatView.jsx`, 5 file task `.agents/tasks/2026-10-20-unify-chat-stream-behavior/`.
- Cập nhật lúc: 2026-10-20T00:00:00+07:00 (ngày hệ thống Tue Oct 20 2026).

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 → AC-04, nhiệm vụ S-01, S-02.
- File/thay đổi cần đọc: toàn bộ diff nêu trên, tập trung tính đúng đắn luồng lỗi, hợp đồng event, bảo trì.
- Bằng chứng kiểm chứng: `verification.md` V-01 (24 pytest passed), V-02 (không regress so với `dev`), V-03 (kiểm chứng tĩnh frontend; E2E `not_run`).
- Điểm cần đánh giá: đúng đắn phân nhánh lỗi trước/sau token đầu; tương thích hợp đồng NDJSON; hành vi caller khác của `stream_answer_with_llm`; nhất quán style code hiện hữu.

## Nhận xét

### R-01 — Phần text nửa vời bị `_normalize_answer_citations` tự nối "[1]"

- Vị trí: `backend/app/api/routes.py`, `chat_stream/event_stream`.
- Liên quan: AC-03.
- Mức độ: `medium`.
- Bắt buộc sửa: có (phát hiện qua test cấp route thất bại lần đầu).
- Trạng thái: `resolved`.
- Vấn đề và tác động: phần text nửa vời không có số trích dẫn nào → hàm chuẩn hóa tự nối `[<first valid id>]`, khiến tin nhắn báo lỗi có câu "Học phí [1]" như câu trả lời hoàn chỉnh — gây hiểu nhầm người đọc và làm test "không nối thêm" thất bại.
- Đề nghị xử lý: bỏ qua chuẩn hóa trích dẫn trên nhánh `stream_error`.
- Người xử lý: `agent-glm-5-3-flash`.
- Phản hồi/cách sửa: thêm nhánh `if stream_error: answer = raw_answer.strip() else: answer = _normalize_answer_citations(...)`.
- Bằng chứng sau sửa: `test_stream_providers_error_after_tokens_emits_error_event_without_fallback` khẳng định `content == "Học phí"` không kèm `[1]`; 24 pytest passed.
- Xác nhận của reviewer: `resolved` — đã đọc lại diff và test sau sửa.

### R-02 — Phần E2E AC-04 chưa chạy trên trình duyệt

- Vị trí: `frontend/src/ChatView.jsx` (S-02).
- Liên quan: AC-04.
- Mức độ: `medium`.
- Bắt buộc sửa: không.
- Trạng thái: `open` (deferred).
- Vấn đề và tác động: frontend không có test harness tự động; việc kiểm tra "hiển thị lỗi + nút gửi lại" mới dừng ở mức đọc code (V-03). Rủi ro nhỏ: UI bubble lỗi đã dùng sẵn CSS/kỹ thuật có sẵn của `failLastMessage`, xác suất hỏng giao diện thấp.
- Đề nghị xử lý: người dùng/coordinator kiểm thử bằng tay trên môi trường dev (dừng LLM giữa chừng hoặc cấu hình key sai) trước khi merge nếu cần đảm bảo trình duyệt.
- Người xử lý: `agent-glm-5-3-flash` (ghi rõ còn thiếu), coordinator quyết định.
- Phản hồi/cách sửa: đã ghi trong `verification.md` V-03 tách bạch `passed` (tĩnh) và `not_run` (E2E) — không đánh tráo trạng thái.
- Bằng chứng sau sửa: không áp dụng.
- Xác nhận của reviewer: không áp dụng.
- Nếu deferred: lý do — không có harness tự động và không có trình duyệt trong phiên; hướng theo dõi — người dùng chạy thử bằng tay trước merge; coordinator ghi nhận quyết định.

### R-03 — Retry phía client gây lưu cặp hỏi–đáp trùng trong DB

- Vị trí: `frontend/src/ChatView.jsx`, `retryLastQuestion` (hành vi có sẵn).
- Liên quan: AC-04 (sát nghĩa "gửi lại câu hỏi").
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open` (deferred).
- Vấn đề và tác động: server đã lưu tin nhắn người dùng + tin nhắn assistant lỗi; khi người dùng bấm "Thử lại", sẽ lưu thêm một cặp hỏi–đáp mới → lịch sử DB có hai lần hỏi cùng câu. Không ảnh hưởng đến câu trả lời hiện tại (frontend chỉ dựng UI từ state cục bộ).
- Đề nghị xử lý: nếu muốn sạch lịch sử, thêm API xóa cặp tin nhắn lỗi hoặc client gửi kèm cờ retry — ngoài phạm vi task này.
- Người xử lý: để dành cho một task khác.
- Phản hồi/cách sửa: không áp dụng.
- Bằng chứng sau sửa: không áp dụng.
- Xác nhận của reviewer: không áp dụng.
- Nếu deferred: hành vi retry không thuộc yêu cầu ban đầu (chỉ yêu cầu "cho phép gửi lại câu hỏi"); tiếp tục theo dõi ở task mới nếu cần.

Không có nhận xét khác. Đã đọc toàn bộ diff trong phạm vi nói trên.

## Lịch sử các vòng review

- 2026-10-20 — agent-glm-5-3-flash — working tree nhánh `fix/chat-stream-consistency` — vòng 1: phát hiện R-01 (test route thất bại), yêu cầu sửa; vòng 2 sau sửa: R-01 `resolved`, R-02/R-03 deferred, `approved`.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có (R-01 đã `resolved`; R-02, R-03 không bắt buộc).
- Nhận xét hoãn lại: R-02 (E2E trình duyệt chưa chạy), R-03 (truy vết lịch sử retry) — có lý do và hướng theo dõi.
- Phần chưa review / giới hạn: frontend E2E trên trình duyệt thực tế chưa được kiểm chứng.
- Bước tiếp theo: người dùng/coordinator commit + merge nếu đồng ý; có thể chạy thử bằng tay R-02 trước khi merge.

# Review: 2026-11-15-chat-status-indicator

- Reviewer: `claude-code`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: nhánh `feat/chat-status-indicator`, diff S-01 trên `5fc10c2`.
- Cập nhật lúc: `2026-11-15T19:10:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: `AC-01`..`AC-06`; nhiệm vụ S-01.
- File/thay đổi đã đọc: `frontend/src/api/health.js`, `api/index.js`, `api/queryClient.js`, `ChatView.jsx`, `styles/chat.css`, `ChatView.test.jsx`, `App.test.jsx`.
- Bằng chứng kiểm chứng: V-01..V-06 trong `verification.md` (đều `passed`; Narrator `not_run`).
- Điểm đã đánh giá: tính đúng đắn, giao diện sáng/tối (dùng token `--warning`/`--danger`/`--text-muted` đã có cho cả hai theme), khả năng truy cập, không đổi hành vi ngoài phạm vi.

## Nhận xét

### R-01 — hai vùng `role="status"` cùng thông báo khi bắt đầu stream

- Vị trí: `frontend/src/ChatView.jsx`, header `.title` và `<p className="sr-only" role="status">`.
- Vấn đề: khi gửi câu hỏi, header đổi thành "Đang trả lời..." và vùng sr-only đổi thành "Đang tìm trong tài liệu..." cùng lúc; trình đọc màn hình có thể đọc cả hai.
- Tác động: thừa một câu thông báo, không mất thông tin.
- Mức độ: `low`; bắt buộc: không.
- Người xử lý: `claude-code`.
- Trạng thái: `deferred`. Lý do: AC-05 yêu cầu vùng header tự thông báo. Muốn bỏ trùng thì tắt `aria-live` của header riêng ở trạng thái `busy`; nên làm sau khi đã nghe bằng Narrator.

### R-02 — trang admin cũng gọi health

- Vị trí: `ChatView` dùng trong `admin/AdminShell.jsx`.
- Vấn đề: tab chat của admin cũng gọi `/api/health` mỗi 60 giây.
- Tác động: thêm một request nhẹ mỗi phút; header admin cũng phản ánh đúng trạng thái.
- Mức độ: `low`; bắt buộc: không.
- Trạng thái: `deferred`. Lý do: plan đã chấp nhận rủi ro này; nếu cần tắt thì thêm prop.

Không có nhận xét `critical`/`high`/`medium`.

Các điểm đã xác nhận đúng:

- Lỗi health mới nhất thắng dữ liệu cũ (`isError` xét trước `data`), nên header không giữ "Sẵn sàng" khi lần kiểm tra mới thất bại; khi kiểm tra sau thành công thì về `ready` (có test).
- Query lỗi vẫn tiếp tục chạy chu kỳ 60 giây và kiểm tra lại khi focus, nên trạng thái tự hồi phục.
- Lỗi 4xx của chat (429/422/413) không kích hoạt kiểm tra health (có test).
- `TypeError` khi stream bị cắt giữa chừng được tính là lỗi kết nối.
- Màu không phải tín hiệu duy nhất: mỗi trạng thái có nhãn chữ riêng; chấm `aria-hidden`.

## Lịch sử các vòng review

- Vòng 1 (`2026-11-15T19:10:00+07:00`): self-review diff S-01, R-01 và R-02 `deferred`, kết luận `approved`.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01, R-02 (đều `low`, không bắt buộc).
- Phần chưa review / giới hạn: chưa có review độc lập; chưa kiểm tra bằng Narrator.
- Bước tiếp theo: merge PR #65 sau khi người yêu cầu duyệt.

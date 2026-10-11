# Verification: <task-id>

- Verifier: `<agent-id>`.
- Trạng thái tổng: `not_run`.
- Bản được kiểm tra: <commit hoặc working tree + các file/phiên bản liên quan>.
- Môi trường: <OS, runtime, dependency liên quan>.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: <agent-id / ISO 8601 có múi giờ>.
- Loại: <test tự động, kiểm tra thủ công hoặc review tài liệu>.
- Thư mục chạy: <đường dẫn>.
- Lệnh / thao tác: <cách tái hiện chính xác>.
- Kỳ vọng: <kết quả cần đạt>.
- Kết quả thực tế: <chưa chạy hoặc đầu ra quan sát được>.
- Trạng thái: `not_run`.
- Bằng chứng: <log, file, ảnh, commit hoặc mô tả quan sát cụ thể>.

### V-02 — AC-02

- Người thực hiện / thời gian: <agent-id / ISO 8601 có múi giờ>.
- Loại: <test tự động, kiểm tra thủ công hoặc review tài liệu>.
- Thư mục chạy: <đường dẫn>.
- Lệnh / thao tác: <cách tái hiện chính xác>.
- Kỳ vọng: <kết quả cần đạt>.
- Kết quả thực tế: <chưa chạy hoặc đầu ra quan sát được>.
- Trạng thái: `not_run`.
- Bằng chứng: <tham chiếu hoặc quan sát cụ thể>.

## Lỗi, kiểm tra lại và phần chưa xác minh

- <Nếu lỗi: gắn AC-*/S-*, người xử lý, kết quả lần kiểm tra lại; giữ lịch sử lỗi trước đó.>
- <Kiểm tra bỏ qua/chưa chạy và lý do; không ghi passed cho kiểm tra chưa chạy.>

## Kết luận

- Tiêu chí đã đạt: <AC-* có bằng chứng>.
- Tiêu chí chưa đạt/chưa xác minh: <AC-* và lý do>.
- Đề xuất: <tiếp tục triển khai, xử lý blocker hoặc cho phép coordinator đánh dấu done>.

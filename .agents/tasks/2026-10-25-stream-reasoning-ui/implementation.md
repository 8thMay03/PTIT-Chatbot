# Implementation: <task-id>

## Tổng quan triển khai

<Các phần đã tích hợp và phần đang chờ. Chưa triển khai thì ghi rõ.>

## Nhật ký theo nhiệm vụ

### S-01 — <agent-id>

- Cập nhật lúc: `<ISO 8601 có múi giờ>`.
- Đã làm: <thay đổi thực tế và lý do>.
- File thay đổi: <đường dẫn>; commit/patch: <tham chiếu nếu có>.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: <chi tiết hoặc không có>.
- Kiểm tra đã chạy: <lệnh, kết quả; liên kết mục tương ứng trong verification.md>.
- Còn lại/blocker: <chi tiết, người cần xử lý, điều kiện tiếp tục>.

## Trao đổi giữa agents

Sao chép khối dưới đây cho mỗi thông báo mới; dùng ID duy nhất. Người nhận thêm phản hồi mới tham chiếu ID gốc, không xóa nội dung cũ.

### MSG-<agent-id>-001

- Lúc: `<ISO 8601 có múi giờ>`.
- Từ: `<agent-id>`; đến: `<agent-id/coordinator>`.
- Nhiệm vụ: `S-01`.
- Loại: `update | question | blocker | decision | handoff | reply` (chọn một).
- Tham chiếu: <ID thông báo trước nếu là phản hồi>.
- Nội dung: <thông tin đủ để người nhận tiếp tục>.
- Hành động mong muốn: <việc cần làm và điều kiện tiếp tục>.

## Bàn giao

### HANDOFF-<agent-id>-001 — S-01

- Từ / đến: `<agent-id>` / `<agent-id>`.
- Đã hoàn tất: <phần việc và đầu ra>.
- File/branch/commit/patch: <tham chiếu; ghi chưa commit nếu phù hợp>.
- Kiểm chứng: <kết quả và liên kết verification.md>.
- Review: <liên kết review.md, kết luận và R-* còn cần xử lý>.
- Hạn chế / còn lại: <vấn đề chưa xử lý>.
- Bước tiếp theo: <hành động của người nhận>.
- Phản hồi nhận bàn giao: <người nhận bổ sung tham chiếu MSG-* xác nhận hoặc câu hỏi>.

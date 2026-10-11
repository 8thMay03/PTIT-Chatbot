# Hướng dẫn làm việc cho AI agents

- Đọc [quy ước phối hợp](.agents/README.md) trước khi bắt đầu công việc.
- Với công việc cần phân công hoặc bàn giao, dùng một thư mục `.agents/tasks/<task-id>/` gồm `task.md`, `plan.md`, `implementation.md`, `verification.md`.
- Tìm task phù hợp đang tồn tại trước khi tạo mới từ `.agents/tasks/_template/`; không coi `_template` là task đang chạy.
- Đọc cả bốn file của task, kiểm tra trạng thái mới nhất và xác nhận nhiệm vụ, phạm vi file, phụ thuộc trước khi sửa mã.
- Chỉ sửa phần việc đã nhận; phối hợp với coordinator trước khi sửa file thuộc agent khác hoặc thay đổi giao diện dùng chung.
- Ghi tiến độ, quyết định, blocker và bàn giao theo quy ước; đọc lại cập nhật liên quan trước khi tiếp tục.
- Không ghi đè thay đổi có sẵn của người dùng hoặc agent khác. Không ghi secret, token hay nội dung `.env` vào nhật ký.
- Chỉ đánh dấu hoàn thành khi các tiêu chí nghiệm thu có bằng chứng kiểm chứng; ghi rõ kiểm tra chưa chạy hoặc còn thất bại.
- Các file này lưu trạng thái phối hợp, không tự khởi chạy agent hay gửi thông báo. Số lượng agent và công cụ liên lạc tuân theo quyền, công cụ có trong phiên làm việc.

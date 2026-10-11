# Plan: 2026-10-11-agent-collaboration

## Phân công

### S-01 — Viết quy ước và mẫu

- Agent: `agent-coordinator`, kiêm triển khai.
- Trạng thái: `done`.
- Mục tiêu: đáp ứng `AC-01`, `AC-02`.
- Phạm vi file: `AGENTS.md`, `.agents/README.md`, `.agents/tasks/_template/*.md`, bốn file trong task này.
- Phụ thuộc: không có.
- Đầu ra: quy ước, mẫu trống và ví dụ có nội dung thực tế.
- Người nhận: `agent-coordinator`, kiêm verifier.

### S-02 — Cho phép lưu Git và kiểm chứng

- Agent: `agent-coordinator`, kiêm verifier.
- Trạng thái: `done`.
- Mục tiêu: kiểm tra `AC-01`, `AC-02`, `AC-03`.
- Phạm vi file: `.gitignore` và kết quả kiểm chứng trong bốn file task này.
- Phụ thuộc: S-01 cung cấp đủ tài liệu.
- Đầu ra: ngoại lệ Git và `verification.md` có bằng chứng.
- Người nhận: chủ repo / agent nhận task tiếp theo.

## Hợp đồng dùng chung

- Không có thay đổi API/schema ứng dụng.
- Bốn tên file và quy tắc trạng thái trong `.agents/README.md` là hợp đồng cho các task sau.
- Một agent thực hiện tuần tự toàn bộ lượt ghi trong phiên này; không có cập nhật đồng thời.

## Thứ tự tích hợp và kiểm chứng

1. Đọc cấu trúc hiện có và `.gitignore`.
2. Tạo quy ước, mẫu, task minh họa và ngoại lệ Git.
3. Kiểm tra đủ file, nội dung quy ước, liên kết nội bộ, trạng thái Git và whitespace.
4. Cập nhật kết quả rồi đóng task nếu tất cả tiêu chí đạt.

## Rủi ro

- `.AGENTS` đã bị ignore: thêm ngoại lệ cho `.agents` ngay sau quy tắc đó.
- Nhiều agent ghi cùng file có thể mất nội dung: quy định lượt ghi tuần tự hoặc coordinator tổng hợp; tài liệu không cung cấp khóa tự động.

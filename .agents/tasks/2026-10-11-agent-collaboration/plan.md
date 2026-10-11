# Plan: 2026-10-11-agent-collaboration

## Phân công ban đầu (trước khi bổ sung review.md)

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
- Năm tên file và quy tắc trạng thái trong `.agents/README.md` là hợp đồng cho các task sau.
- Một agent thực hiện tuần tự toàn bộ lượt ghi trong phiên này; không có cập nhật đồng thời.

## Thứ tự tích hợp và kiểm chứng ban đầu

1. Đọc cấu trúc hiện có và `.gitignore`.
2. Tạo quy ước, mẫu, task minh họa và ngoại lệ Git.
3. Kiểm tra đủ file, nội dung quy ước, liên kết nội bộ, trạng thái Git và whitespace.
4. Cập nhật kết quả rồi đóng task nếu tất cả tiêu chí đạt.

## Bổ sung review theo yêu cầu tiếp theo

### S-03 — Bổ sung review.md và điều kiện hoàn tất

- Agent: `agent-coordinator`, kiêm triển khai, verifier và reviewer.
- Trạng thái: `done`.
- Mục tiêu: cập nhật AC-01, kiểm tra lại AC-02/AC-03 và đáp ứng AC-04.
- Phạm vi file: `AGENTS.md`, `.agents/README.md`, năm file mẫu và năm file task minh họa này.
- Phụ thuộc: S-01, S-02 đã hoàn tất; task được mở lại theo yêu cầu người dùng.
- Đầu ra: mẫu review, review thực tế, quy ước năm file và bằng chứng kiểm tra lại.
- Người nhận: chủ repo / agent nhận việc tiếp theo.
- Hình thức review: `self_review`; không có reviewer độc lập trong phiên này.
- Thứ tự: cập nhật tài liệu → kiểm tra cấu trúc/liên kết/Git → tự review diff và bằng chứng → kết luận review → đóng task.

## Rủi ro

- `.AGENTS` đã bị ignore: thêm ngoại lệ cho `.agents` ngay sau quy tắc đó.
- Nhiều agent ghi cùng file có thể mất nội dung: quy định lượt ghi tuần tự hoặc coordinator tổng hợp; tài liệu không cung cấp khóa tự động.

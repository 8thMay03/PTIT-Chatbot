# Task: Thiết lập phối hợp agents qua file

- ID: `2026-10-11-agent-collaboration`
- Trạng thái: `done`
- Coordinator: `agent-coordinator` (agent thực hiện trong phiên này)
- Người yêu cầu: chủ repo PTIT Chatbot
- Tạo lúc: `2026-10-11T21:24:19+07:00`
- Cập nhật lúc: `2026-10-11T21:26:06+07:00`

## Yêu cầu và kết quả mong muốn

Lưu các task trong `.agents` để nhiều AI agents có thể phối hợp cùng mục tiêu, nhận nhiệm vụ khác nhau và bàn giao bằng `task.md`, `plan.md`, `implementation.md`, `verification.md`.

## Phạm vi

- Tạo hướng dẫn gốc, quy ước trong `.agents`, bộ mẫu và task minh họa này.
- Cho phép Git theo dõi `.agents` bằng ngoại lệ trong `.gitignore`.
- Không thay đổi chức năng ứng dụng. Không bổ sung bộ điều phối hoặc khóa file tự động.

## Tiêu chí nghiệm thu

- [x] AC-01: Bộ mẫu và task minh họa đều có đúng bốn file yêu cầu.
- [x] AC-02: Hướng dẫn có phân công, phụ thuộc, trao đổi, bàn giao, tránh xung đột và điều kiện hoàn thành có kiểm chứng.
- [x] AC-03: Git nhận các file trong `.agents`; đường dẫn Markdown nội bộ hợp lệ và thay đổi không có lỗi whitespace.

## Tài liệu và phụ thuộc

- [Quy ước phối hợp](../../README.md).
- [Hướng dẫn cho agent](../../../AGENTS.md).
- Không có phụ thuộc chức năng ứng dụng.

## Trạng thái hiện tại

- Đã tạo bộ mẫu, hướng dẫn, task minh họa và ngoại lệ Git; mọi tiêu chí nghiệm thu đạt theo `verification.md`.
- Blocker: không có.
- Bước tiếp theo: chủ repo hoặc agent tiếp theo tạo task mới từ bộ mẫu khi có mục tiêu mới.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-11T21:24:19+07:00` — `agent-coordinator`: dùng tài liệu chung làm kênh phối hợp bất đồng bộ; trong phiên thiết lập này một agent kiêm triển khai và kiểm chứng.
- `2026-10-11T21:26:06+07:00` — `agent-coordinator`: kết thúc rà soát, ba tiêu chí đạt, chuyển task sang `done`.

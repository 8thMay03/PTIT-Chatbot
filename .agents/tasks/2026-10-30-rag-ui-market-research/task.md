# Task: Nghiên cứu giao diện hệ thống RAG trên thị trường và đề xuất thay đổi giao diện

- ID: `2026-10-30-rag-ui-market-research`
- Trạng thái: `in_review`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng (yêu cầu trực tiếp trong phiên chat)
- Tạo lúc: `2026-10-30T23:42:16+07:00`
- Cập nhật lúc: `2026-10-30T23:42:16+07:00`

## Yêu cầu và kết quả mong muốn

Người dùng: "research giao diện của hệ thống RAG đã có sẵn trên thị trường và đề xuất thay đổi giao diện hiện
tại của hệ thống".

Kết quả cần có: một tài liệu tiếng Việt gồm (1) hiện trạng giao diện chat có bằng chứng, (2) khảo sát các sản
phẩm RAG trên thị trường có dẫn nguồn, (3) các mẫu thiết kế rút ra, (4) danh sách đề xuất thay đổi có ưu tiên,
thay đổi API cần thiết và lộ trình, (5) mockup minh hoạ.

## Phạm vi

- Bao gồm: `docs/design/RAG-UI-Market-Research.md`, `docs/design/mockups/chat-proposed.html`,
  `docs/design/assets/*.png`, năm file task này.
- Ngoài phạm vi: không sửa mã nguồn ứng dụng, không implement đề xuất (mỗi giai đoạn trong lộ trình là task riêng).
- Ràng buộc: nhận định về hiện trạng phải chỉ ra file/ảnh chụp; nhận định về sản phẩm khác phải có nguồn; ghi rõ
  giới hạn nghiên cứu (không dùng thử trực tiếp, một số trang không truy cập được).

## Tiêu chí nghiệm thu

- [x] AC-01: Tài liệu có mục hiện trạng với các vấn đề `H-*`, mỗi vấn đề kèm file hoặc ảnh chụp làm bằng chứng.
- [x] AC-02: Khảo sát tối thiểu 6 sản phẩm/hệ thống RAG, có bảng so sánh mẫu thiết kế và danh sách nguồn có link.
- [x] AC-03: Đề xuất `D-*` có ưu tiên, liên kết tới vấn đề `H-*`, nêu thay đổi API cần có và cách hoạt động khi
  API chưa có.
- [x] AC-04: Có mockup giao diện đề xuất và ảnh so sánh với giao diện hiện tại.
- [x] AC-05: Nêu phối hợp/xung đột với task đang chạy và các câu hỏi cần người dùng quyết định.

## Tài liệu và phụ thuộc

- `.agents/tasks/2026-10-21-uiux-redesign-context/` — hướng thị giác "Học vụ hiện đại" (đề xuất đi theo).
- `.agents/tasks/2026-10-28-landing-user-auth/` (`in_progress`) — cùng chạm `App.jsx` (header/sidebar chat).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã viết tài liệu, mockup, ảnh chụp; self-review `approved`. Chờ người dùng đọc và trả lời các câu hỏi
  ở §9 của tài liệu trước khi lập task triển khai.
- Blocker: không có.
- Bước tiếp theo: người dùng chọn đề xuất/giai đoạn cần làm → coordinator lập task triển khai riêng.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-30T23:42:16+07:00` — `claude-agent`: tạo task, làm một mình (khảo sát, viết, self-review), chuyển
  `in_review` chờ người dùng phản hồi đề xuất.

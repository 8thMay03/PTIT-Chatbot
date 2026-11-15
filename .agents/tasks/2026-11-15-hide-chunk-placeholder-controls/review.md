# Review: 2026-11-15-hide-chunk-placeholder-controls

- Reviewer: `claude-code`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: diff S-01 trên nhánh `feat/hide-chunk-placeholder-controls` (nền `a2891b2`).
- Cập nhật lúc: `2026-11-15T21:10:44+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: `AC-01`..`AC-04`; nhiệm vụ S-01.
- File đã đọc: `frontend/src/DocumentView.jsx`, `frontend/src/styles/document.css`, `frontend/src/DocumentView.pagination.test.jsx`.
- Bằng chứng kiểm chứng: V-01..V-04 trong `verification.md`.
- Điểm đã đánh giá: tính đúng đắn, giao diện, khả năng truy cập, không đổi hành vi ngoài phạm vi.

## Nhận xét

- Đúng đắn: không còn tham chiếu tới state/handler đã gỡ (build pass, grep sạch). `label` vẫn được dùng cho `chunk-index-tag`. `handleChunkHover` và effect xoá highlight không đổi.
- Giao diện: gỡ rule `.chunk-card-top` có `space-between` là cần thiết, vì nếu giữ thì nhãn token sẽ dạt sang mép phải khi thẻ chỉ còn hai nhãn. Thanh công cụ vẫn `space-between`: số đoạn bên trái, nhóm chế độ/tìm kiếm bên phải, như trước.
- Truy cập: mỗi thẻ bớt hai điều khiển tương tác, nên phím Tab bớt điểm dừng vô nghĩa. Thẻ đoạn vốn là `div` có `onClick`, không dùng được bằng bàn phím. Điều này có từ trước và nằm ngoài phạm vi (task không đổi hover/click), nên không tạo nhận xét bắt buộc.
- `pill-switch` trong `dataset.css` vẫn được `ConfigView.jsx` dùng, nên giữ lại là đúng.

Không có nhận xét `R-*` bắt buộc.

## Lịch sử các vòng review

- `2026-11-15T21:10:44+07:00` — vòng 1, self_review: `approved`.

## Kết luận

- Kết luận: `approved` (self_review).
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: không có.
- Phần chưa review / giới hạn: chưa xem giao diện thực tế trên trình duyệt (xem `verification.md`).
- Bước tiếp theo: người yêu cầu xem trực quan, push và mở PR.

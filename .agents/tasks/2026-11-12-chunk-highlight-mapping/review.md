# Review: 2026-11-12-chunk-highlight-mapping

- Reviewer: `claude-code`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: working tree trên `feat/chunk-highlight-mapping`.
- Cập nhật lúc: `2026-11-12T23:58:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-03; S-01.
- File: `frontend/src/lib/chunkLocator.js`, `frontend/src/lib/chunkLocator.test.js`, `frontend/src/DocumentView.jsx`.
- Bằng chứng: V-01…V-03.

## Nhận xét

Không có nhận xét bắt buộc. Đã kiểm tra:
- An toàn: Markdown của đoạn đi qua `renderMarkdownHtml` (đã sanitize) trước khi gán `innerHTML` vào phần tử tách rời.
- Bộ định vị lập lại khi phần tử render hoặc nội dung tài liệu đổi; cache theo danh sách đoạn bị xóa khi danh sách đổi (đổi trang, tìm kiếm).
- Đệ quy định vị đoạn trước chỉ chạy khi mơ hồ, sâu tối đa bằng số đoạn trên trang.

Giới hạn đã biết (không bắt buộc sửa):
- Đoạn bảng bị chia nhỏ có header lặp: khi header nằm gần (≤ ~2 hàng) phần thân, vùng đánh dấu có thể kèm 1–2 hàng của đoạn trước (ví dụ #774).
- Đoạn đầu tiên của trang không có đoạn đứng trước trong danh sách; nếu nội dung trùng hoàn toàn ở nhiều chỗ thì phân xử theo tỷ lệ chunk_index.

## Lịch sử các vòng review

- 2026-11-12T23:58:00+07:00 — claude-code — working tree — `approved` (self_review).

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Phần chưa review / giới hạn: self_review, không phải review độc lập; chưa kiểm tra trên trình duyệt.

# Task: Công tắc bật/tắt và ô chọn đoạn ở màn tài liệu không có tác dụng thật

- ID: `2026-11-15-hide-chunk-placeholder-controls`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-15T11:08:52+07:00`
- Cập nhật lúc: `2026-11-15T21:10:44+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: rà soát giao diện frontend ngày 2026-11-15 (lỗi số 7). Phát hiện khi đọc mã; màn quản trị chưa chạy được vì backend tắt.

Hành vi hiện tại trong `frontend/src/DocumentView.jsx` (đối chiếu trên `dev` @ `0fdd444`):

- Mỗi thẻ đoạn có công tắc bật/tắt (`pill-switch`, dòng 662-671). Công tắc chỉ đổi state cục bộ `enabledChunks` (dòng 71): không gọi API, tải lại trang là mất, và đoạn "tắt" vẫn được dùng khi chatbot trả lời. Chỉ tooltip ghi "trạng thái này chưa được máy chủ lưu lại".
- Mỗi thẻ có ô chọn (dòng 647-653) và thanh công cụ có "Chọn tất cả" (dòng 544-556). Chúng cập nhật `selectedChunkIds` (dòng 70) nhưng không thao tác nào dùng đến lựa chọn này.
- Nhãn loại đoạn "Văn bản" viết cứng (dòng 659) cho mọi đoạn.

Tác động: quản trị viên có thể tưởng đã tắt một đoạn sai khỏi kho tri thức trong khi thực tế không có gì thay đổi.

Kết quả cần có: màn chi tiết tài liệu không hiển thị điều khiển không có tác dụng thật, cho đến khi backend hỗ trợ.

## Phạm vi

- Bao gồm: `frontend/src/DocumentView.jsx` (gỡ công tắc, ô chọn, "Chọn tất cả" và state, handler đi kèm); `frontend/src/styles/document.css` (dọn style không còn dùng, giữ bố cục thẻ gọn); test.
- Ngoài phạm vi: API bật/tắt đoạn và lọc đoạn bị tắt khi truy xuất (cần task backend riêng nếu muốn làm thật); thay đổi hover/click định vị đoạn trên văn bản; phân trang đoạn.
- Ràng buộc: không làm hỏng tính năng định vị đoạn (`lib/chunkLocator`, task `2026-11-12-chunk-highlight-mapping`) và phân trang (`2026-11-12-chunk-pagination-fix`).

## Tiêu chí nghiệm thu

- [x] AC-01: Màn chi tiết tài liệu không còn công tắc bật/tắt đoạn, ô chọn từng đoạn và "Chọn tất cả". State `enabledChunks`, `selectedChunkIds` cùng các handler đi kèm được gỡ khỏi mã.
- [ ] AC-02: Thẻ đoạn vẫn gọn (không chừa khoảng trống chỗ điều khiển cũ). Rê chuột và bấm vào thẻ vẫn định vị đoạn trên văn bản; test hiện có (`DocumentView.pagination.test.jsx`, test của `chunkLocator`) pass.
- [x] AC-03: Nhãn loại đoạn xử lý theo Q-02.
- [x] AC-04: `npm test` và `npm run build` pass.

## Tài liệu và phụ thuộc

- Code: `frontend/src/DocumentView.jsx`, `frontend/src/styles/document.css`, `frontend/src/lib/chunkLocator*`.
- Task liên quan đã xong: `2026-11-12-chunk-highlight-mapping`, `2026-11-12-chunk-pagination-fix`.
- Không có task đang mở nào khác cùng sửa `DocumentView.jsx`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Câu hỏi mở cho người yêu cầu

- Q-01: Ẩn hay làm thật? Đề xuất **gỡ khỏi giao diện ở task này**. Nếu cần bật/tắt đoạn thật thì mở task riêng gồm API backend, lọc khi truy xuất và giao diện.
- Q-02: Nhãn "Văn bản" viết cứng. Đề xuất **gỡ luôn**, vì nhãn cố định không mang thông tin. Phương án khác: hiện loại đoạn thật nếu dữ liệu đoạn có trường phân biệt (ví dụ bảng); cần kiểm tra schema API đoạn trước.

## Trạng thái hiện tại

- Tóm tắt: S-01 đã triển khai trên nhánh `feat/hide-chunk-placeholder-controls` theo đề xuất mặc định Q-01, Q-02. Kiểm tra tự động đạt; self_review `approved`.
- Blocker: không có.
- Bước tiếp theo: xem trực quan thẻ đoạn trên trình duyệt (phần thủ công của AC-02 chưa chạy), push và mở PR vào `dev`, rồi đóng task.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-15T11:08:52+07:00 — claude-code: tạo task `draft` từ kết quả rà soát giao diện ngày 2026-11-15 theo yêu cầu "với mỗi lỗi hãy tạo 1 task".
- 2026-11-15T21:10:44+07:00 — claude-code: người yêu cầu giao triển khai ("implement"); chốt Q-01 = gỡ khỏi giao diện, Q-02 = gỡ nhãn "Văn bản" theo đề xuất mặc định. Chuyển `in_review`. AC-02 chưa tick vì phần kiểm tra thủ công chưa chạy.

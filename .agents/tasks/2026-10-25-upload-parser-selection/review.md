# Review: 2026-10-25-upload-parser-selection

- Reviewer: `claude-code`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `dev` trên `b27f320` (diff S-01, S-02).
- Cập nhật lúc: `2026-10-25T14:00:25+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-04, S-01, S-02.
- File/thay đổi cần đọc: toàn bộ `git diff` của 7 file trong phạm vi.
- Bằng chứng kiểm chứng: V-01…V-04.
- Điểm cần đánh giá: tương thích ngược API upload, tệp hỗn hợp định dạng, đóng/hủy modal khi đang tải, lỗi mạng khi lấy danh sách parser.

## Nhận xét

### R-01 — Ghi chú "tệp không hỗ trợ parser này" hiện cả khi chọn parser mặc định

- Vị trí: `frontend/src/components/ParserSelectionModal.jsx` (`idleText`).
- Liên quan: AC-03.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: với tệp hỗn hợp (PDF + MD), ghi chú vẫn hiện khi chọn Docling. Nội dung vẫn đúng (MD dùng parser Text mặc định), chỉ hơi thừa.
- Đề nghị xử lý: chỉ hiện khi parser được chọn không phải mặc định, nếu người dùng thấy gây nhầm lẫn.
- Người xử lý: `claude-code`.
- Nếu deferred: theo dõi phản hồi người dùng; coordinator ghi nhận.

Ngoài R-01: tương thích ngược giữ nguyên (`parser_name` chỉ truyền khi có; test cũ dùng lambda 2 tham số vẫn pass); modal không đóng được khi `busy`; kéo-thả khi modal đang mở bị bỏ qua (`uploadTarget`); `GET /parsers` chỉ dùng đuôi file, không chạm hệ thống tệp.

## Lịch sử các vòng review

- `2026-10-25T14:00:25+07:00` — claude-code — working tree S-01, S-02 — approved, R-01 deferred.

## Kết luận

- Kết luận: `approved` (self_review, không phải review độc lập).
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01.
- Phần chưa review / giới hạn: chưa thử tải lên thật bằng LlamaParse.
- Bước tiếp theo: người dùng thử thật và commit.

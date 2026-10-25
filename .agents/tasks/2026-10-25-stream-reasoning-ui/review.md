# Review: <task-id>

- Reviewer: `<agent-id>`.
- Hình thức: `<independent | self_review>` (chọn một).
- Trạng thái: `pending`.
- Bản được review: <commit hoặc working tree + diff/phạm vi file cụ thể>.
- Cập nhật lúc: `<ISO 8601 có múi giờ>`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: <AC-* và nhiệm vụ S-* liên quan>.
- File/thay đổi cần đọc: <đường dẫn và phạm vi diff>.
- Bằng chứng kiểm chứng: <mục V-* trong verification.md; ghi rõ phần chưa kiểm chứng>.
- Điểm cần đánh giá: <tính đúng đắn, trường hợp lỗi, tương thích, bảo mật, khả năng bảo trì hoặc tính nhất quán tài liệu theo phạm vi task>.

## Nhận xét

Khối dưới là mẫu, chưa phải nhận xét thực tế. Thay bằng các nhận xét có ID duy nhất; nếu đã review và không có vấn đề, ghi rõ không có nhận xét kèm phạm vi đã đọc.

### R-01 — <Tên vấn đề>

- Vị trí: <file:dòng hoặc mục cụ thể>.
- Liên quan: <AC-*/S-*>.
- Mức độ: `<critical | high | medium | low>` (chọn một).
- Bắt buộc sửa: <có/không; critical và high luôn có>.
- Trạng thái: `open`.
- Vấn đề và tác động: <quan sát cụ thể, tình huống xảy ra, hậu quả>.
- Đề nghị xử lý: <kết quả cần đạt>.
- Người xử lý: `<agent-id>`.
- Phản hồi/cách sửa: <người triển khai bổ sung hoặc gửi reviewer tổng hợp>.
- Bằng chứng sau sửa: <diff/commit và kiểm tra liên quan>.
- Xác nhận của reviewer: <kết quả review lại; chỉ resolved khi đã xác nhận>.
- Nếu deferred: <lý do, hướng theo dõi và quyết định của coordinator; chỉ áp dụng với nhận xét không bắt buộc>.

## Lịch sử các vòng review

- <Thời gian> — <reviewer> — <bản/phạm vi> — <kết luận và các R-* liên quan>.

## Kết luận

- Kết luận: `pending`.
- Nhận xét bắt buộc còn mở: <R-* hoặc không có, sau khi đã review>.
- Nhận xét hoãn lại: <R-* và hướng theo dõi, hoặc không có>.
- Phần chưa review / giới hạn: <ghi rõ>.
- Bước tiếp theo: <agent xử lý / verifier kiểm tra lại / coordinator đóng task khi đủ điều kiện>.

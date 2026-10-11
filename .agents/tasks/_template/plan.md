# Plan: <task-id>

## Phân công

### S-01 — <Tên nhiệm vụ>

- Agent: `<agent-id>`
- Trạng thái: `todo`
- Mục tiêu: <kết quả cụ thể>; phục vụ `AC-01`.
- Phạm vi file được sửa: <đường dẫn cụ thể>.
- Phụ thuộc: <không có hoặc S-* + điều kiện sẵn sàng>.
- Đầu ra/bàn giao: <file, hợp đồng, commit/patch nếu có>.
- Người nhận: `<agent-id>`.

### S-02 — <Tên nhiệm vụ>

- Agent: `<agent-id khác hoặc cùng agent nếu làm tuần tự>`
- Trạng thái: `todo`
- Mục tiêu: <kết quả cụ thể>; phục vụ `AC-02`.
- Phạm vi file được sửa: <đường dẫn cụ thể>.
- Phụ thuộc: <S-01 hoặc không có nếu thực sự độc lập>.
- Đầu ra/bàn giao: <kết quả cần có>.
- Người nhận: `<coordinator/verifier>`.

## Hợp đồng dùng chung

- <Tên API/schema/interface, bên cung cấp, bên sử dụng, cấu trúc và lỗi dự kiến. Ghi không áp dụng nếu chỉ sửa tài liệu.>
- File mã nguồn dùng chung và người sửa: <đường dẫn + agent-id>.
- Lượt ghi năm file task: <coordinator tổng hợp hoặc thứ tự agent được ghi; không ghi đồng thời>.

## Phân công kiểm chứng và review

- Verifier: `<agent-id>`; phạm vi kiểm chứng: <AC-* và kiểm tra liên quan>.
- Reviewer: `<agent-id>`; phạm vi review: <nhiệm vụ/file cần đánh giá>.
- Hình thức review: `<independent | self_review>` (chọn một theo người thực hiện thực tế).
- Người xử lý nhận xét: <agent phụ trách từng phần; reviewer xác nhận sau khi sửa>.

## Thứ tự tích hợp và kiểm chứng

1. <Các nhiệm vụ có thể chạy độc lập và điều kiện bắt đầu>.
2. <Coordinator tích hợp, giải quyết file chung và thông báo bản mới>.
3. <Verifier thực hiện kiểm tra tương ứng AC-* trên bản đã tích hợp>.
4. <Reviewer ghi nhận xét trong review.md; agent phụ trách sửa, verifier kiểm tra lại và reviewer xác nhận trên bản mới>.
5. <Coordinator đối chiếu tiêu chí, kết luận review approved và không còn nhận xét bắt buộc chưa xử lý rồi đóng task>.

## Rủi ro và điều chỉnh kế hoạch

- <Rủi ro, cách xử lý, người phụ trách; ghi thay đổi kế hoạch và lý do khi phát sinh.>

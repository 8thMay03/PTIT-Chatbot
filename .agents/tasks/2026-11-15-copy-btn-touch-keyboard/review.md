# Review: 2026-11-15-copy-btn-touch-keyboard

- Reviewer: `claude-code`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: nhánh `feat/copy-btn-touch-keyboard` @ `3e8922a` (diff `a57ce4b..3e8922a`).
- Cập nhật lúc: `2026-11-15T21:05:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: `AC-01`..`AC-04`; nhiệm vụ S-01.
- File/thay đổi đã đọc: `frontend/src/styles/chat.css`, `frontend/src/styles/layout.css`; đối chiếu `base.css` (`:focus-visible`), `ChatView.jsx` (`.bubble-actions`), `ConversationList.jsx` (`.conv-actions`), các file CSS khác không ghi đè opacity của hai lớp này.
- Bằng chứng kiểm chứng: V-01..V-04 trong `verification.md`, đều `passed`.
- Điểm đã đánh giá: tính đúng đắn, giao diện sáng/tối, khả năng truy cập, không đổi hành vi ngoài phạm vi.

## Nhận xét

### R-01 — Nút còn hiện sau khi bấm bằng chuột trên desktop

- Vị trí: `frontend/src/styles/chat.css`, `.bubble-wrap:focus-within .bubble-actions`.
- Vấn đề: bấm "Sao chép" bằng chuột để lại focus trên nút, nên hàng nút vẫn hiện sau khi rời chuột cho tới khi focus chuyển đi.
- Tác động: chỉ là hiển thị, giống hành vi `.conv-actions` đã có từ trước. Đổi sang `:has(:focus-visible)` sẽ tránh được nhưng làm khác cách viết của sidebar.
- Mức độ: `low`; bắt buộc sửa: không.
- Người xử lý: không cần.
- Trạng thái: `deferred`. Lý do: nhất quán với `.conv-actions`, và còn có lợi (người dùng thấy nhãn "Đã chép"). Xem lại nếu có phản hồi từ người dùng.

### Ghi nhận khác (không phải nhận xét)

- Giao diện sáng/tối: chỉ đổi `opacity`, không đổi màu hay token, nên không ảnh hưởng theme.
- Trình đọc màn hình: `opacity: 0` vốn không ẩn khỏi cây truy cập; không đổi gì.
- `(hover: none)` thay vì `(any-hover: none)` khớp quyết định rủi ro trong `plan.md`.
- Không có thay đổi ngoài phạm vi: không sửa DOM, kích thước nút hay luồng sao chép.

## Lịch sử các vòng review

- Vòng 1 (`2026-11-15T21:05:00+07:00`, bản `3e8922a`): `approved`, R-01 `low` hoãn lại.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01 (`low`).
- Phần chưa review / giới hạn: chưa thử trên điện thoại thật; đây là self_review, không phải review độc lập.
- Bước tiếp theo: mở PR vào `dev`.

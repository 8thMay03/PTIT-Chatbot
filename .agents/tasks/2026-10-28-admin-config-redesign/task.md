# Task: Thiết kế lại màn hình cấu hình hệ thống (Cấu hình RAG) của admin

- ID: `2026-10-28-admin-config-redesign`
- Trạng thái: `in_review`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng (yêu cầu trực tiếp trong phiên chat)
- Tạo lúc: `2026-10-28T23:20:00+07:00`
- Cập nhật lúc: `2026-10-28T23:47:00+07:00`

## Yêu cầu và kết quả mong muốn

Người dùng: "thiết kế lại giao diện màn hình config hệ thống của admin sao cho trông dễ nhìn, dễ thao tác".

Hiện trạng tab Settings → Cấu hình RAG (`frontend/src/ConfigView.jsx`):

- Bốn thẻ xếp hai cột lệch chiều cao, thứ tự không theo luồng xử lý (LLM trước, truy xuất sau).
- Nhãn, giá trị, gợi ý chen chúc trên một dòng; gợi ý canh phải bị xuống dòng, chip giá trị bị gãy ("4 đoạn").
- Giá trị hiển thị ba lần (chip, thanh trượt, ô số); ô số kẹp giá trị ngay khi gõ nên khó nhập.
- Nút Lưu chỉ ở đầu trang; cuộn xuống thì không thấy trạng thái chưa lưu, không biết trường nào đã sửa,
  không có cách bỏ thay đổi ngoài tải lại trang.
- Cài đặt phụ (số truy vấn phụ, hệ số ứng viên) biến mất khi tắt công tắc cha, khó phát hiện.

Kết quả cần có: bố cục một cột dễ đọc theo các bước của pipeline RAG, có mục lục điều hướng, mỗi cài đặt là một
dòng "nhãn + giải thích | điều khiển", đánh dấu trường đã sửa, hoàn tác từng trường / toàn bộ, thanh lưu luôn
hiển thị, hoạt động tốt trên mobile và dark mode. Giữ nguyên hợp đồng API `/config` và hành vi đồng bộ cache
với tab Mô hình.

## Phạm vi

- Bao gồm: `frontend/src/ConfigView.jsx`, `frontend/src/styles/config.css`, `frontend/src/styles/responsive.css`
  (bỏ style cũ không còn dùng), test mới `frontend/src/ConfigView.test.jsx`.
- Ngoài phạm vi: tab Mô hình (`ModelsView.jsx`), tab Giao diện, khung `SettingsView.jsx`, backend, thêm tham số
  cấu hình mới, thay đổi khoảng giá trị/giá trị mặc định.
- Ràng buộc: không đổi payload `PUT /config`, `POST /config/reset`; giữ `mergeConfigDraft`; giữ các
  `id`/`aria-label` mà test hiện có dựa vào; chỉ dùng token màu trong `tokens.css`.

## Tiêu chí nghiệm thu

- [x] AC-01: Các nhóm cài đặt xếp theo luồng truy xuất → xếp hạng lại → lọc → sinh câu trả lời, có mục lục
  bấm để cuộn tới nhóm và tóm tắt giá trị hiện tại.
- [x] AC-02: Mỗi cài đặt hiển thị nhãn, giải thích, điều khiển rõ ràng; thanh trượt có nhãn min/max, ô số
  có đơn vị, chỉ nhận giá trị hợp lệ khi gõ và kẹp về khoảng khi rời ô.
- [x] AC-03: Trường đã sửa được đánh dấu và hoàn tác được riêng; thanh lưu cố định ở đáy cho biết số thay đổi,
  có "Huỷ thay đổi" và "Lưu cấu hình" (Ctrl/Cmd+S khi tab đang hiển thị).
- [x] AC-04: Cài đặt phụ thuộc công tắc vẫn hiển thị nhưng bị khoá khi công tắc tắt.
- [x] AC-05: Bố cục dùng được ở desktop, tablet, mobile (390px) và dark mode.
- [x] AC-06: Không hồi quy: toàn bộ test frontend, build và `check:bundle` đạt.

## Tài liệu và phụ thuộc

- `2026-10-21-uiux-redesign-context` (token/màu), `2026-10-27-fe02-api-client` (cache cấu hình dùng chung),
  `2026-10-27-fe06-admin-separation` (app quản trị).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai và kiểm chứng trên nhánh `feat/admin-config-redesign`; self-review không có nhận xét
  bắt buộc. Chờ người dùng xem giao diện và quyết định merge vào `dev`.
- Blocker: không có.
- Bước tiếp theo: người dùng xem lại giao diện; coordinator merge khi được đồng ý rồi chuyển `done`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-10-28T23:20:00+07:00 — claude-agent: tạo task, giới hạn ở tab Cấu hình RAG vì đây là màn
  "Cấu hình hệ thống & tham số RAG"; tab Mô hình giữ nguyên.
- 2026-10-28T23:47:00+07:00 — claude-agent: chuyển `in_review` sau khi kiểm chứng đạt.

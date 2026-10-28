# Task: Hiệu ứng chuyển động cho trang chat `/chat`

- ID: `2026-10-28-chat-motion`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("thêm hiệu ứng vào trang ở /chat nữa", nối tiếp task `2026-10-28-landing-motion`)
- Tạo lúc: `2026-10-28T21:31:42+07:00`
- Cập nhật lúc: `2026-10-28T21:41:30+07:00`

## Yêu cầu và kết quả mong muốn

Landing đã có bộ chuyển động theo phong cách eduardbodak.com; trang chat mới chỉ có `msgIn` (tin nhắn trượt lên
10 px), chấm "đang nghĩ" và con trỏ nhấp nháy. Cần đưa cùng ngôn ngữ chuyển động sang `/chat`, nhưng ở mức hợp với
màn làm việc: không che nội dung, không làm chậm thao tác, không gây rối khi đọc câu trả lời dài.

Kết quả cần có:

1. Pixel transition "tan ra" khi vào trang (từ landing và giữa các trang có pixel transition), đóng R-04 của task
   landing-motion; link về landing/đăng nhập trong chat cũng đi qua pixel transition.
2. Màn vào trang: sidebar, header, composer xuất hiện so le; màn chào: icon bật vào rồi lơ lửng, tiêu đề hiện theo
   từ, thẻ gợi ý trượt lên so le, nghiêng theo chuột kèm vệt sáng, sóng khi click.
3. Tin nhắn: câu hỏi trượt vào từ phải, câu trả lời từ trái; mở lại hội thoại thì các tin hiện so le (có giới hạn);
   nguồn trích dẫn trượt vào lần lượt; trích dẫn được bấm nháy sáng; lỗi rung nhẹ.
4. Trạng thái làm việc: avatar trợ lý có vòng sáng xoay khi đang trả lời, chấm trạng thái header phát sóng khi đang
   trả lời, các bước suy luận trượt vào khi xuất hiện, viền khung nhập chạy sáng khi đang trả lời/được focus.
5. Nút: nút gửi/dừng đổi icon có chuyển cảnh, nút "xuống tin mới nhất" bật vào, danh sách hội thoại hiện so le.

## Phạm vi

- Bao gồm: `frontend/src/lib/motion/*` (chuyển lõi dùng chung từ `landing/motion/`), `frontend/src/landing/*` (chỉ
  sửa import), `frontend/src/main.jsx` (chạy pixel "vào trang"), `frontend/src/App.jsx`, `frontend/src/ChatView.jsx`,
  `frontend/src/components/{UserMenu,ConversationList,ReasoningPanel}.jsx` (chỉ thêm class/thuộc tính),
  `frontend/src/styles/{motion,chat-motion,landing-motion,index}.css`, test.
- Ngoài phạm vi: hành vi chat (stream, lưu hội thoại), nội dung chữ, trang admin, trang đăng nhập/đăng ký (chỉ hưởng
  pixel "vào trang" dùng chung).
- Ràng buộc:
  - Không thêm thư viện; giữ hợp đồng bundle (chunk chat không chứa module admin, không vượt mốc FE-06; landing không
    chứa module chat).
  - `prefers-reduced-motion: reduce` hoặc thiếu `matchMedia` → không pixel, không tilt; animation CSS rút về tức thì
    (quy tắc sẵn có trong `base.css`), nội dung luôn hiện.
  - Không tự cuộn hay đổi focus khác hành vi hiện có; không animate khi người dùng đang đọc (chỉ phần tử mới mount).

## Tiêu chí nghiệm thu

- [x] AC-01: Đủ 5 nhóm hiệu ứng, quan sát được trên trình duyệt thật (ảnh chụp khung hình giữa chuyển động).
- [x] AC-02: Pixel "vào trang" chỉ chạy khi trang trước vừa chạy pixel transition (cờ `sessionStorage` còn hạn), không
  chặn thao tác (`pointer-events: none`) và tự gỡ; không chạy khi giảm chuyển động.
- [x] AC-03: Giảm chuyển động: không lớp phủ, không animation vô hạn trang trí, nội dung hiện ngay.
- [x] AC-04: Test sẵn có của chat (`App.test.jsx`, …) giữ nguyên kỳ vọng và đạt; 360/768/1280 sáng/tối không cuộn ngang.
- [x] AC-05: `npm test`, `npm run build`, `npm run check:bundle` đạt; ghi kích thước gzip trang chat trước/sau.

## Tài liệu và phụ thuộc

- Task trước: `.agents/tasks/2026-10-28-landing-motion/` (`done`, đã merge `dev` tại `f5d49a9`).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: `done` — S-01 … S-04 xong, V-01 … V-05 `passed`, review `self_review` `approved` (R-02, R-03 deferred).
- Blocker: không.
- Bước tiếp theo: người dùng xem `/chat`; quyết định R-03 (nền header chủ đề tối, có từ trước).

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-28T21:31:42+07:00` — `claude-agent`: tạo task, chuyển thẳng `in_progress` theo yêu cầu trực tiếp.
- `2026-10-28T21:41:30+07:00` — `claude-agent`: hoàn tất, chuyển `done`.

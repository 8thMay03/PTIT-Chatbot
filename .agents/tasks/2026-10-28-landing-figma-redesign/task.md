# Task: Làm lại trang landing theo thiết kế Figma "AI Chat landing page UI kit"

- ID: `2026-10-28-landing-figma-redesign`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng (yêu cầu trực tiếp trong phiên chat)
- Tạo lúc: `2026-10-28T09:09:12+07:00`
- Cập nhật lúc: `2026-10-28T09:25:00+07:00`

## Yêu cầu và kết quả mong muốn

Người dùng muốn trang landing (`/`, làm ở task `2026-10-28-landing-user-auth`) trông như thiết kế Figma
<https://www.figma.com/design/eFjnqtVcNbPLWXV6HXA5CE/AI-Chat-landing-page-UI-kit--Community-?node-id=2002-456>
(frame "AI Chat", 1440 × 5875; node `1:1947` là ảnh bìa của cùng bộ kit) và đề xuất cải thiện UI.

Thiết kế gồm: thanh điều hướng; hero hai dòng tiêu đề serif, mô tả, nút tối, hai thẻ nghiêng trang trí, khung
soạn câu hỏi và nền chữ mờ; dải logo đối tác; khối tính năng dạng bento 5 thẻ; carousel lời chứng thực; FAQ dạng
accordion; dải kêu gọi hành động; footer nền tối.

## Phạm vi

- Bao gồm: `frontend/src/landing/*`, `frontend/src/styles/landing.css`, token màu landing trong
  `frontend/src/styles/tokens.css`, font tự host (`@fontsource/readex-pro`, `@fontsource/playfair-display`), điền
  sẵn câu hỏi ở `/chat?q=` (`frontend/src/App.jsx`, `frontend/src/ChatView.jsx`), chỉnh nhẹ trang đăng nhập/đăng ký
  cho cùng phong cách (font + nút), test frontend.
- Ngoài phạm vi: màn chat/admin (ngoài nhận `?q=`), backend, đổi nội dung pháp lý/thông tin chưa có nguồn.
- Ràng buộc:
  - Nội dung trung thực (D-10 task trước): không logo đối tác, không lời chứng thực hay số liệu bịa, không quảng cáo
    tính năng không có (giọng nói, chọn model). Các khối của thiết kế được giữ bố cục nhưng thay nội dung thật.
  - CSS thuần, chỉ `tokens.css` chứa màu thô; icon `lucide-react`; không thêm thư viện UI/animation.
  - Giữ AC của task trước: landmark, một `h1`, sáng/tối, 360/768/1280 không cuộn ngang, landing không tải module
    chat/admin (`check:bundle`).
  - Font thiết kế "PP Editorial New" là font thương mại, không có bản quyền web và không có dấu tiếng Việt → thay
    bằng Playfair Display (serif tương phản cao, hiển thị đúng dấu tiếng Việt); "Readex Pro" dùng đúng font gốc.

## Tiêu chí nghiệm thu

- [x] AC-01: `/` dựng lại đủ các khối của frame `2002:456` theo thứ tự, đúng font/khoảng cách/màu chính (đối chiếu
  ảnh chụp thiết kế và ảnh chụp bản dựng ở 1440 px), nội dung tiếng Việt trung thực.
- [x] AC-02: Khung soạn câu hỏi ở hero hoạt động: chip chủ đề điền câu gợi ý, gửi mở `/chat?q=<câu hỏi>`; trang
  chat điền sẵn câu hỏi vào ô nhập (không tự gửi) và xoá `q` khỏi URL.
- [x] AC-03: Carousel "Cách hoạt động" và FAQ dùng được bằng bàn phím, có `aria-expanded`/`aria-controls`, nhãn nút.
- [x] AC-04: Sáng/tối, 360/768/1280 px không cuộn ngang; vẫn một `h1`, landmark `header/main/footer`.
- [x] AC-05: `npm test`, `npm run build`, `npm run check:bundle` đạt; landing không chứa module chat/admin.

## Tài liệu và phụ thuộc

- Dựa trên nhánh `feat/landing-user-auth` (task `2026-10-28-landing-user-auth`, chưa merge `dev`) vì landing chỉ có
  ở nhánh đó.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: `done` — S-01 … S-04 xong, V-01 … V-05 `passed`, review `self_review` `approved`.
- Blocker: không.
- Bước tiếp theo: người dùng xem landing; quyết định R-03 (giữ nền trung tính theo Figma hay đổi sang maroon).

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-28T09:09:12+07:00` — `claude-agent`: tạo task từ yêu cầu người dùng; đọc thiết kế qua connector Figma
  (asset URL của Figma bị chặn mạng trong phiên nên icon dùng `lucide-react`, nền mờ/chữ gradient dựng bằng CSS).
- `2026-10-28T09:25:00+07:00` — `claude-agent`: hoàn tất, chuyển `done`.

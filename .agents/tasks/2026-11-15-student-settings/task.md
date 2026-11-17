# Task: Cài đặt cho sinh viên

- ID: `2026-11-15-student-settings`
- Trạng thái: `in_review`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("tạo task cải thiện đi", sau tài liệu nghiên cứu màn Cài đặt)
- Tạo lúc: `2026-11-15T23:42:56+07:00`
- Cập nhật lúc: `2026-11-17T22:14:33+07:00`

## Yêu cầu và kết quả mong muốn

Giai đoạn 3 của lộ trình trong `docs/design/Settings-Market-Research.md` §8, đề xuất D-06.

**Hiện trạng** (H-08):

- App sinh viên (`/chat`) chỉ có hộp thoại "Giao diện" với 3 nút chủ đề (`App.jsx:269-281`).
- Tài khoản là tên + icon đăng xuất trên header (`UserMenu.jsx`).
- Không có nơi quản lý dữ liệu: chỉ xoá được từng hội thoại trong sidebar.
- Không chỉnh được cỡ chữ.
- Phím gửi cố định là Enter (`ChatView.jsx:851`, `lib/keyboard.js`).
- Panel suy luận luôn tự thu gọn khi câu trả lời bắt đầu hiện (`ChatView.jsx:355-363`).

**Kết quả cần có**: hộp thoại "Cài đặt" (desktop: danh mục trái; mobile: toàn màn hình) gồm ba nhóm:

- **Chung**: giao diện, cỡ chữ, gửi bằng Enter, giữ mở quá trình suy luận. Tự lưu trên thiết bị.
- **Tài khoản**: tên, email, đăng xuất.
- **Dữ liệu & lịch sử**: tải lịch sử, xoá toàn bộ hội thoại. Phạm vi nhóm này theo quyết định Q-03.

Mockup tham chiếu: `docs/design/mockups/settings-proposed.html` khung B (desktop) và C (mobile).

## Phạm vi

- Bao gồm:
  - Frontend:
    - `frontend/src/App.jsx`, `frontend/src/components/UserMenu.jsx`, `frontend/src/components/ThemePicker.jsx`.
    - `frontend/src/ChatView.jsx` (phím gửi, panel suy luận, dòng gợi ý dưới ô nhập).
    - Component mới trong `frontend/src/student-settings/` (hoặc `components/StudentSettings*.jsx`).
    - Module tùy chọn `frontend/src/lib/preferences.js` (+ test), `frontend/src/lib/keyboard.js` (+ test).
    - `frontend/src/styles/tokens.css` / `base.css` (cỡ chữ), style của hộp thoại.
    - Test `App.test.jsx`, `ChatView.test.jsx`.
  - Backend (khi Q-03 chọn "Xoá toàn bộ"): `backend/app/api/routes.py`, `backend/app/db/repositories.py`, test mới cho
    `DELETE /api/conversations`.
- Ngoài phạm vi: đổi mật khẩu, đổi tên, xoá tài khoản (cần API mới, task sau); cho sinh viên chọn mô hình/temperature
  (§7 tài liệu: không đề xuất); đa ngôn ngữ giao diện; Settings của admin.
- Ràng buộc:
  - Chunk trang chat không được import mã admin (`SettingsView`, `ConfigView`, `ModelsView`…); `npm run check:bundle`
    phải xanh.
  - Mọi đọc/ghi localStorage bọc try/catch (theo cách `lib/theme.js` đang làm). Storage bị chặn thì giao diện vẫn chạy
    với giá trị mặc định.
  - Giữ hành vi IME của `isSubmitEnter`: Enter chốt chữ bộ gõ không được gửi tin.
  - Hash cũ `#settings/appearance` (`lib/appRoute.js` `isAppearanceHash`) mở hộp thoại Cài đặt ở mục Chung.
  - Dùng `Modal` hiện có (focus trap, Esc, trả focus).
  - Tùy chọn trong nhóm Chung tự lưu (toggle/segmented, theo Primer), có phản hồi "Đã lưu trên thiết bị này".
  - Nhánh `feat/student-settings` tách từ `dev`; commit message tiếng Anh.

## Tiêu chí nghiệm thu

- [x] AC-01: Lối vào:
  - Mục sidebar "Giao diện" đổi thành "Cài đặt" và mở hộp thoại Cài đặt; `#settings/appearance` mở thẳng mục Chung.
  - Chip tài khoản thành menu có "Cài đặt" và "Đăng xuất"; khách thấy "Đăng nhập". Vị trí chip (header hay chân sidebar)
    theo quyết định Q-02.
  - Có test cho hai lối vào và hash.
- [x] AC-02: Hộp thoại:
  - Từ 768px trở lên: danh mục trái (Chung, Tài khoản khi đã đăng nhập, Dữ liệu & lịch sử) và nội dung phải.
  - Dưới 768px: toàn màn hình, các nhóm xếp thành danh sách, có nút đóng.
  - Bàn phím đi được qua danh mục và điều khiển; Esc đóng; focus trả về nút đã mở.
- [x] AC-03: Nhóm Chung, mỗi thay đổi áp dụng ngay, giữ sau khi tải lại trang:
  - Giao diện: sáng/tối/hệ thống, dùng `useTheme`.
  - Cỡ chữ: Nhỏ/Vừa/Lớn (Vừa là cỡ hiện tại), có đoạn xem trước. Áp dụng cho câu hỏi, câu trả lời, trích dẫn, ô nhập.
    Bố cục không vỡ ở 390px với cỡ Lớn.
  - Gửi bằng Enter (mặc định bật). Tắt thì Enter xuống dòng, Ctrl+Enter (Cmd+Enter trên macOS) gửi, dòng gợi ý dưới ô
    nhập đổi theo. Enter chốt chữ IME không gửi tin.
  - Giữ mở quá trình suy luận (mặc định tắt). Bật thì panel không tự thu gọn khi câu trả lời bắt đầu stream.
  - Có test cho hàm đọc/ghi tùy chọn (kể cả storage lỗi), phím gửi và panel suy luận.
- [x] AC-04: Nhóm Tài khoản (chỉ khi đã đăng nhập): tên, email, nút Đăng xuất dùng `useLogout`. Đăng xuất xong thì đóng
  hộp thoại và đưa chat về hội thoại mới như `handleLoggedOut` hiện tại.
- [x] AC-05 (theo Q-03): Nhóm Dữ liệu & lịch sử.
  - "Tải lịch sử về máy": tạo tệp Markdown gồm tiêu đề, câu hỏi, câu trả lời, nguồn trích dẫn của mọi hội thoại thuộc
    phiên hiện tại (phân trang `GET /api/conversations`, rồi `GET /api/conversations/{id}`).
  - "Xoá toàn bộ hội thoại":
    - Đặt trong thẻ "Vùng nguy hiểm" ở cuối; hộp xác nhận nêu số hội thoại và "không thể hoàn tác".
    - Gọi `DELETE /api/conversations`. Endpoint mới xoá mọi hội thoại của `owner_key` hiện tại (tài khoản hoặc ẩn danh)
      và trả `{ deleted: <số> }`.
    - Xoá xong thì sidebar làm mới và chat về hội thoại mới.
  - Test backend chứng minh không xoá hội thoại của owner khác, và cookie admin không đổi owner (giống
    `GET /conversations`).
  - Nếu Q-03 bỏ mục nào thì ghi `cancelled` cho phần đó cùng lý do.
- [x] AC-06: `npm test`, `npm run build`, `npm run check:bundle` (`frontend/`) xanh; `python -m pytest` (`backend/`) xanh
  nếu có thay đổi backend. Có ảnh chụp desktop 1366×768 và mobile 390×844, sáng và tối, gồm cỡ chữ Lớn.

## Tài liệu và phụ thuộc

- `docs/design/Settings-Market-Research.md` §2.3 (H-08), §5 (D-06), §6, §10 (Q-02, Q-03).
- `docs/design/mockups/settings-proposed.html` khung B, C.
- `.agents/tasks/2026-10-30-rag-ui-market-research/` D-08: đề xuất chuyển khu tài khoản xuống chân sidebar (liên quan
  Q-02).
- Các task `2026-11-15-chat-header-*` vừa sửa header chat: đọc lại trạng thái trước khi sửa `App.jsx`/`UserMenu.jsx`.
- Độc lập với hai task Settings admin (`2026-11-15-settings-gate-savebar`, `2026-11-15-settings-nav-retrieval-test`):
  khác file, có thể làm song song.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01 … S-05 xong trên `feat/student-settings` (`c491a2f`); V-01 … V-06 `passed`; self_review `approved`
  (5 nhận xét `low` hoãn lại).
- Quyết định của người dùng (2026-11-17): **Q-02** chân thanh bên; **Q-03** làm cả "Tải lịch sử" và "Xoá toàn bộ".
- Blocker: không có.
- Bước tiếp theo: người dùng duyệt; push nhánh và mở PR vào `dev` khi được đồng ý, merge xong chuyển `done`.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-11-15T23:42:56+07:00` — `claude-agent`: tạo task từ giai đoạn 3 của tài liệu nghiên cứu (chỉ D-06; D-08 chuyển
  sang `2026-11-15-settings-nav-retrieval-test`); trạng thái `ready`, hai phần chờ Q-02/Q-03.
- `2026-11-17T22:14:33+07:00` — `claude-agent`: người dùng trả lời Q-02 (chân thanh bên), Q-03 (cả hai mục); triển
  khai đủ phạm vi, không mục nào `cancelled`; chuyển `in_review` chờ người dùng duyệt PR.

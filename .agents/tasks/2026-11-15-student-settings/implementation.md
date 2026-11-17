# Implementation: 2026-11-15-student-settings

## Tổng quan triển khai

- Nhánh `feat/student-settings` (tách từ `dev` tại `72a45b5`; `git pull origin dev` báo "Already up to date").
- Commit mã nguồn: `c491a2f` (`feat: add student settings dialog with preferences, account menu and data controls`).
- Người dùng trả lời (2026-11-17, qua câu hỏi trong phiên):
  - **Q-02**: khu tài khoản ở **chân thanh bên**.
  - **Q-03**: làm **cả hai** "Tải lịch sử về máy" và "Xoá toàn bộ hội thoại".
  - Working tree có thay đổi không thuộc task (xoá `data/Sổ tay sinh viên D26 _1_.pdf`, tài liệu nghiên cứu chưa
    commit): người dùng đồng ý tạo nhánh và giữ nguyên, không commit các thay đổi đó.
- Trước khi sửa `App.jsx`/`UserMenu.jsx`: `2026-11-15-chat-header-dark-bg` ghi `in_review` nhưng PR #63 đã merge
  (`gh pr view 63`: `MERGED`), `2026-11-15-chat-header-new-chat-button` là `done`; cả hai đã có trong `dev`.

## Nhật ký theo nhiệm vụ

### S-02 — Module tùy chọn và áp dụng (`done`)

- `frontend/src/lib/preferences.js` (mới): khoá `ptit_chatbot_prefs` = `{ version: 1, fontScale, enterToSend,
  keepReasoningOpen }`, mặc định `{ "md", true, false }`. `readPreferences`/`writePreferences` bọc try/catch; JSON
  hỏng, `version` khác hoặc giá trị lạ → mặc định. `usePreferences()` trả các giá trị + `setPreference(key, value)`
  (trả `false` khi không lưu được, vẫn áp dụng trong phiên). Ghi storage đồng bộ qua ref, không ghi trong updater của
  setState (StrictMode có thể chạy updater hai lần).
- Cỡ chữ: `applyFontScale` đặt `<html data-font-scale="sm|lg">` (bỏ thuộc tính với `md`); rời trang chat thì gỡ.
  `tokens.css` thêm `--chat-font-scale` (1 / 0.875 / 1.125). `chat.css` nhân hệ số cho bubble (câu hỏi + câu trả
  lời), chip trích dẫn, thẻ nguồn (nhãn, số, tên, tài liệu, mục), ô nhập. Không đổi `--text-*` toàn cục nên thanh
  bên và màn admin không bị ảnh hưởng. Đo bằng Chromium: `md` giữ đúng cỡ cũ (bubble 16px, ô nhập 15px).
- Chống nháy cỡ chữ lúc tải trang: **không làm** (phải thêm script inline vào `index.html` và đổi hash CSP ở
  `frontend/nginx/page-headers.conf`). Cỡ chữ áp dụng sau khi React mount; ghi trong verification/review (R-01).
- `frontend/src/lib/keyboard.js`: thêm `isSubmitKey(event, { enterToSend })` (tắt: chỉ Ctrl/Cmd+Enter gửi) và
  `isApplePlatform()`; nhánh IME giữ nguyên cho cả hai chế độ.
- `frontend/src/ChatView.jsx`: prop `enterToSend` (mặc định `true`) và `keepReasoningOpen` (mặc định `false`); app
  admin không truyền nên giữ hành vi cũ. `keepReasoningOpen` đọc qua ref để đổi giữa lượt vẫn có hiệu lực. Dòng gợi ý
  dưới ô nhập đổi theo (`Ctrl + Enter` hoặc `⌘ + Enter` trên macOS).

### S-01 — Lối vào và khung hộp thoại (`done`)

- `frontend/src/student-settings/StudentSettingsDialog.jsx` (mới) dùng `Modal` hiện có (focus trap, Esc, trả focus).
  `Modal` thêm prop `className` (tương thích ngược, mặc định rỗng) để hộp thoại có bố cục riêng.
- Bố cục (`frontend/src/styles/student-settings.css`, import trong `index.css`):
  - Từ 768px: header "Cài đặt" + nút đóng; danh mục trái (Chung, Tài khoản khi đã đăng nhập, Dữ liệu & lịch sử);
    nội dung mục đang chọn.
  - Dưới 768px: toàn màn hình, ẩn danh mục, mọi nhóm xếp thành danh sách có tiêu đề nhóm; mở thẳng nhóm được yêu
    cầu thì cuộn tới nhóm đó.
- `App.jsx`: state `settingsSection` (`null | general | account | data`) thay `appearanceOpen`; mục sidebar
  "Giao diện" đổi thành "Cài đặt" (icon `Settings`); `#settings/appearance` mở mục Chung (lúc tải và khi
  `hashchange`), đóng thì bỏ hash như trước. Bỏ `Modal`/`ThemePicker` khỏi `App.jsx`.
- Trên mobile mở Cài đặt từ drawer **không** đóng drawer nữa: hộp thoại phủ toàn màn hình (`z-index: 50` qua
  `.modal-backdrop:has(> .student-settings)`, trên drawer 45, dưới toast 60), nên khi đóng focus về đúng nút trong
  drawer (drawer đóng thì nút bị `inert`, focus mất).
- `components/UserMenu.jsx` (theo Q-02): chip ở chân thanh bên (avatar, tên, email) là nút `aria-haspopup="menu"`;
  menu `role="menu"` có "Cài đặt" và "Đăng xuất"; mũi tên/Home/End đi giữa mục, Esc đóng và trả focus về chip
  (chặn lan để không đóng drawer), Tab đóng và trả focus về chip, bấm ngoài hoặc đổi kích thước cửa sổ thì đóng.
  Khách thấy link "Đăng nhập" dạng mục thanh bên. Bỏ chip khỏi header chat.
  - Menu render qua portal vào `document.body`, vị trí `fixed` tính từ chip: phía trên chip khi thanh bên mở, bên
    phải chip khi thanh bên thu gọn (`compact`). Lý do: hiệu ứng vào trang `animation … both` trên con của
    `.sidebar` biến chân thanh bên thành containing block + stacking context, nên menu nằm trong thanh bên bị cắt
    (thanh bên `overflow: hidden`) và bị `main-pane` đè (phát hiện khi chụp ảnh thanh bên thu gọn).
  - `layout.css`: style khối tài khoản cho nền maroon; bỏ style cũ của chip trên header và `.user-login-btn`.
- `ThemePicker.jsx` chỉ còn dùng ở admin; sửa comment.

### S-03 — Nội dung nhóm Chung và Tài khoản (`done`)

- Chung: "Giao diện" (radiogroup Sáng/Tối/Theo hệ thống, dùng `useTheme`), "Cỡ chữ" (Nhỏ/Vừa/Lớn + đoạn xem trước
  có chip trích dẫn), "Gửi bằng Enter" và "Giữ mở quá trình suy luận" (`role="switch"`). Segmented dùng roving
  tabindex + mũi tên. Mỗi thay đổi hiện "✓ Đã lưu trên thiết bị này" (`role="status"`); storage lỗi thì "Không lưu
  được trên thiết bị này; chỉ áp dụng đến khi tải lại trang."
- Tài khoản (chỉ khi đã đăng nhập): avatar, tên, email, nút "Đăng xuất" dùng `useLogout`; xong thì gọi
  `handleLoggedOut` của App (chat về hội thoại mới) và đóng hộp thoại.

### S-04 — Dữ liệu & lịch sử (`done`)

- Backend:
  - `repositories.delete_conversations_for_owner(session, owner_key)`: xoá qua ORM từng hội thoại của đúng owner
    (Message/MessageSource xoá theo như `delete_conversation`), kể cả hội thoại rỗng; owner rỗng không xoá gì.
  - `DELETE /api/conversations` trong `routes.py`: owner từ `auth.get_client_session(...).owner_key`,
    `client.apply(response)`, trả `{ "deleted": <int> }`. Thêm vào `PUBLIC_API_ROUTES` (test quét route admin vẫn
    xanh). Không đè `DELETE /conversations/{conversation_id}`.
  - Test mới `backend/tests/test_conversation_bulk_delete.py` (5 test).
- Frontend:
  - `api/conversations.js`: `removeAll()`.
  - `lib/exportConversations.js` (mới): `fetchAllConversations` phân trang `limit=200`, tải chi tiết song song tối đa
    4 request, báo tiến độ; `conversationsToMarkdown` (tiêu đề, ngày bắt đầu, câu hỏi, câu trả lời, nguồn
    `[n] locator — tài liệu — mục`, ghi chú câu trả lời bị dừng/lỗi); `exportFileName`; `downloadTextFile`.
  - Nhóm Dữ liệu: "Tải lịch sử về máy" (nút hiện `Đang tải x/y`, toast kết quả; tắt khi chưa có hội thoại). "Vùng
    nguy hiểm" ở cuối với "Xoá toàn bộ…".
  - Xác nhận xoá là **khung xác nhận ngay trong thẻ** (`role="alertdialog"`, focus vào "Huỷ"), không phải modal lồng:
    `Modal` đăng ký Esc/Tab ở `document` pha capture, hai modal lồng nhau sẽ cùng nhận Esc (đóng cả hộp thoại ngoài)
    và tranh focus trap. Nội dung: "Xoá vĩnh viễn **N hội thoại**? Thao tác này không thể hoàn tác." (N = `total`
    của danh sách hội thoại).
  - Xoá xong: `resetQueries(conversations)` (sidebar tải lại), App đưa chat về hội thoại mới, toast "Đã xoá N hội
    thoại."; hộp thoại vẫn mở và hiện "Chưa có hội thoại nào.".

### S-05 — Kiểm chứng và ảnh chụp (`done`)

- Xem `verification.md`. Ảnh + số đo trong `evidence/` (chụp bằng `playwright-core` + Chromium đã cài, API giả lập
  qua `page.route(http://localhost:5191/api/**)`).

## Trao đổi giữa agents

- Một agent (`claude-agent`) làm mọi vai trò; không có thông báo giữa agents.

## Bàn giao

- `2026-11-17T22:14:33+07:00` — `claude-agent` → người dùng:
  - Đã làm: S-01 … S-05 trên `feat/student-settings` (`c491a2f`); verification V-01 … V-06 `passed`; self_review
    `approved` (không có nhận xét bắt buộc; 5 nhận xét `low` hoãn lại, xem `review.md`).
  - Chưa làm: chưa push nhánh, chưa mở PR vào `dev` (chờ người dùng đồng ý). Thay đổi không thuộc task trong working
    tree vẫn để nguyên, không commit.
  - Ảnh hưởng chung: thêm `DELETE /api/conversations` (route công khai mới); `Modal` có prop `className`; `UserMenu`
    đổi API (`onOpenSettings`, `compact`), chỉ `App.jsx` dùng.
  - Ghi chú cho tài liệu nghiên cứu: `docs/design/Settings-Market-Research.md` §10 (chưa commit, thuộc task
    `2026-11-15-settings-market-research`) chưa đánh dấu Q-02/Q-03 đã trả lời; câu trả lời ghi ở `task.md` này.

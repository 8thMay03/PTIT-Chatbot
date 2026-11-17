# Verification: 2026-11-15-student-settings

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: nhánh `feat/student-settings`, commit `c491a2f` (tách từ `dev` `72a45b5`).
- Môi trường: Windows 11, Node v24.14.0, Vitest 3.2.7 (jsdom), Python venv `backend/.venv`; ảnh chụp bằng
  `playwright-core` 1.49.1 + Chromium `chromium-1234`, Vite dev server cổng 5191, `/api/**` giả lập.
- Cập nhật lúc: `2026-11-17T22:14:33+07:00`.

## Kiểm chứng tiêu chí

### V-01 — AC-01 (lối vào)

- Loại: test tự động `frontend/src/App.test.jsx`.
- Test liên quan:
  - "không có lối vào Dataset/Settings…": nhãn sidebar có "Cài đặt", không còn "Giao diện".
  - "mục Cài đặt trên thanh bên mở hộp thoại ở mục Chung…".
  - "#settings/appearance mở hộp thoại Cài đặt ở mục Chung": lúc tải trang và khi `hashchange`; đóng thì bỏ hash;
    không chuyển trang.
  - "khách thấy Đăng nhập ở chân thanh bên (không ở header)…".
  - "đã đăng nhập: chip ở chân thanh bên mở menu Cài đặt/Đăng xuất…": menu có đúng hai mục, focus mục đầu, mũi tên,
    Esc và Tab trả focus về chip, menu nằm ngoài container (portal), đăng xuất về khách.
  - "menu tài khoản → Cài đặt…".
- Kết quả: `passed` (lệnh ở V-06).
- Ảnh: `evidence/account-menu-desktop-{light,dark}.png`, `account-menu-collapsed-light.png` (thanh bên thu gọn, menu
  mở sang phải), `guest-sidebar-light.png`, `sidebar-mobile-{light,dark}.png`.

### V-02 — AC-02 (hộp thoại)

- Loại: test tự động + đo bằng Chromium (`evidence/ui-checks.json`) + ảnh 1366×768 và 390×844.
- Kết quả:
  - Desktop 1366: danh mục trái + nội dung (`settings-desktop-*.png`). Khách chỉ có Chung, Dữ liệu & lịch sử (test
    và `settings-desktop-data-guest-light.png`); đã đăng nhập có thêm Tài khoản.
  - Mobile 390: hộp thoại rộng 390px, `.ss-body` scrollWidth = clientWidth = 390 (không tràn ngang), 3 nhóm cùng hiển
    thị, có nút đóng (`settings-mobile-*.png`, `settings-mobile-bottom-*.png`). Mở từ drawer: hộp thoại phủ lên
    drawer (lần chụp đầu thấy drawer đè hộp thoại → đã sửa z-index, chụp lại).
  - Bàn phím (Chromium thật): Tab từ khi mở lần lượt `Đóng cài đặt` → `Chung` → `Tài khoản` → `Dữ liệu & lịch sử` →
    radio `Sáng` → radio `Vừa` → switch → switch → quay về `Đóng cài đặt` (focus trap). Mũi tên phải trên segmented
    cỡ chữ đổi sang `lg`. Esc đóng hộp thoại, focus về nút "Cài đặt" đã mở.
  - Test jsdom: Esc đóng và focus về nút sidebar / chip đã mở; nút đóng; `aria-current` trên mục danh mục; mũi tên
    trên segmented đổi lựa chọn và focus.
- Trạng thái: `passed`.

### V-03 — AC-03 (nhóm Chung)

- Loại: test tự động + đo Chromium + ảnh.
- Test:
  - `lib/preferences.test.js` (9): chuẩn hoá, đọc/ghi + `version`, JSON hỏng/`version` khác → mặc định, storage chặn
    (getItem/setItem ném lỗi) → mặc định và ghi trả `false`, `applyFontScale`, hook giữ giá trị sau khi mount lại,
    gỡ `data-font-scale` khi unmount, storage chặn vẫn áp dụng trong phiên.
  - `lib/keyboard.test.js` (7): `isSubmitKey` bật/tắt Enter, Ctrl/Cmd+Enter, IME (`isComposing`, `keyCode` 229) không
    gửi ở cả hai chế độ; `isApplePlatform`.
  - `ChatView.test.jsx`: gợi ý mặc định; tắt Enter → Enter không gửi và không `preventDefault`, Ctrl+Enter chốt chữ IME
    không gửi, Ctrl+Enter và Cmd+Enter gửi, gợi ý "Ctrl + Enter để gửi · Enter để xuống dòng"; panel suy luận mặc
    định thu gọn khi có `delta`, bật `keepReasoningOpen` thì vẫn mở.
  - `App.test.jsx`: đổi chủ đề (radiogroup, `data-theme`), cỡ chữ Lớn đặt `data-font-scale="lg"`, tắt Enter đổi gợi
    ý ngay, "Đã lưu trên thiết bị này", localStorage đúng hợp đồng; unmount rồi mount lại App giữ cả ba tùy chọn.
- Đo Chromium (`ui-checks.json`, desktop, hội thoại có nguồn):

  | Cỡ | Bubble | Chip trích dẫn | Tên nguồn | Ô nhập | Mục sidebar |
  | --- | --- | --- | --- | --- | --- |
  | Nhỏ | 14px | 9.625px | 10.94px | 13.125px | 13px |
  | Vừa | 16px | 11px | 12.5px | 15px | 13px |
  | Lớn | 18px | 12.375px | 14.06px | 16.875px | 13px |

  "Vừa" khớp cỡ trước thay đổi; sidebar không đổi.
- Mobile 390 cỡ Lớn, sáng và tối: `document.scrollWidth = 390`, không bubble/thẻ nguồn/khung nhập nào vượt mép phải
  (`chat-mobile-lg-*.png`, `chat-mobile-lg-sources-*.png`). Desktop cỡ Lớn: `chat-desktop-lg-light.png`.
- Giới hạn đã biết: cỡ chữ áp dụng sau khi React mount (không sửa script inline/CSP), có thể thấy cỡ "Vừa" trong
  khoảnh khắc lúc tải trang với người chọn Nhỏ/Lớn. Chưa đo bằng mắt trên máy thật.
- Trạng thái: `passed`.

### V-04 — AC-04 (Tài khoản)

- Loại: test tự động (`App.test.jsx` "menu tài khoản → Cài đặt…") + ảnh `settings-desktop-account-{light,dark}.png`.
- Kết quả: mục Tài khoản có tên và email; bấm "Đăng xuất" gọi `POST /auth/logout`, hộp thoại đóng, thanh bên về link
  Đăng nhập, danh sách hội thoại của tài khoản biến mất. Khách không có mục Tài khoản (V-02).
- Trạng thái: `passed`.

### V-05 — AC-05 (Dữ liệu & lịch sử)

- Backend: `.venv/Scripts/python -m pytest tests/test_conversation_bulk_delete.py tests/test_admin_auth.py -q` →
  `142 passed`. Các test mới:
  - xoá mọi hội thoại ẩn danh và tin nhắn, trả `{"deleted": 2}`; owner chưa có hội thoại → `{"deleted": 0}`;
  - không đụng hội thoại của tài khoản khác và của phiên ẩn danh khác;
  - cookie admin không đổi owner: admin chỉ xoá hội thoại của chính trình duyệt đó (`{"deleted": 1}`), hội thoại của
    sinh viên còn nguyên;
  - `DELETE /conversations/{id}` vẫn hoạt động.
- Frontend:
  - `lib/exportConversations.test.js` (5): phân trang (offset 0/3/6), tối đa 4 request chi tiết song song, giữ thứ tự,
    dừng khi trang rỗng, Markdown có tiêu đề/câu hỏi/câu trả lời/nguồn/ghi chú bị dừng, tên tệp theo ngày.
  - `App.test.jsx` "tải lịch sử…": gọi `GET /conversations?limit=200&offset=0` và `GET /conversations/conv-tk`, tạo
    Blob Markdown có nội dung hội thoại, tải tệp `ptit-chatbot-lich-su-YYYY-MM-DD.md`.
  - `App.test.jsx` "xoá toàn bộ…": thẻ "Vùng nguy hiểm"; xác nhận nêu "1 hội thoại" và "không thể hoàn tác", focus
    vào "Huỷ"; chưa xác nhận thì không gọi API; xác nhận → `DELETE /api/conversations`, sidebar tải lại rỗng, chat
    về màn chào, hiện "Chưa có hội thoại nào.".
- Ảnh: `settings-desktop-data-{light,dark}.png` (đang xác nhận), `settings-mobile-bottom-*.png`.
- Không mục nào bị bỏ (Q-03 chọn cả hai).
- Trạng thái: `passed`.

### V-06 — AC-06 (lệnh và ảnh)

- `frontend/`: `npx vitest run` (cùng lệnh `npm test`) → `Test Files 45 passed (45)`, `Tests 379 passed (379)`.
- `frontend/`: `npm run build` → `✓ built`.
- `frontend/`: `npm run check:bundle` → "check:bundle đạt.", JS ban đầu trang chat gzip 89.80 kB (mốc 128.41 kB);
  không có module admin trong chunk chat.
- `backend/`: `.venv/Scripts/python -m pytest -q` → `1356 passed, 24 skipped, 1 warning`.
- Ảnh (`evidence/`): desktop 1366×768 và mobile 390×844, sáng và tối, gồm cỡ chữ Lớn (chat và hộp thoại).
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chụp đầu:
  - Mobile: drawer thanh bên (z-index 45) đè lên hộp thoại (40) → thêm z-index 50 cho backdrop của hộp thoại này, chụp
    lại `settings-mobile-*`.
  - Thanh bên thu gọn: menu tài khoản bị cắt/đè và `focus()` cuộn ngang thanh bên → chuyển menu sang portal + vị trí
    tính từ chip, `focus({ preventScroll: true })`; chạy lại toàn bộ test và chụp lại.
- Chưa xác minh: cỡ chữ trên thiết bị iOS/Android thật; trình đọc màn hình thật (chỉ kiểm thuộc tính ARIA và focus).
  Ảnh dùng API giả lập.

## Kết luận

- Tiêu chí đã đạt: `AC-01` … `AC-06`.
- Tiêu chí chưa đạt/chưa xác minh: không có (giới hạn ghi ở trên).
- Đề xuất: chuyển review.

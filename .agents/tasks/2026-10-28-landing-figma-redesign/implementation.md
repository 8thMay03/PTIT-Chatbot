# Implementation: 2026-10-28-landing-figma-redesign

## Tổng quan triển khai

- Nhánh: `feat/landing-figma-redesign` (tách từ `feat/landing-user-auth` tại `053b561`).
- Đọc thiết kế qua connector Figma (`get_design_context`, `get_screenshot` dạng base64) cho các node `2002:572`
  (nav), `2002:614`/`2002:473`/`2002:535`/`2002:462` (hero), `2002:664`/`2002:776`/`2002:802` (bento),
  `2002:940` (carousel), `2002:997` (FAQ), `2002:1053` (footer); `1:1947` là ảnh bìa bộ kit.
- Không tải được asset từ `www.figma.com/api/mcp/asset/*` (proxy trả 403) → icon dùng `lucide-react` (quy ước dự
  án), các SVG trang trí (vệt mờ nền, chữ gradient, micro phát sáng) dựng lại bằng CSS.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent (token, font, CSS)

- Lúc: `2026-10-28T09:10:00+07:00` → `09:22:01+07:00`.
- `frontend/src/styles/tokens.css`: thêm bộ token `--lp-*` (sáng + hai khối tối) theo màu Figma (`#191D24`,
  `#566273`, `#E9E9EA`, `#F6F6F7`, `#CACBCD`, gradient nút `#212730 → #3D3D3D`, nền thẻ `#F6F6F6 → #FFF4F0`, màu
  nhãn). Chế độ tối: nút chính đảo sang nền sáng, nhãn tối `#3A3F48`, chữ nền mờ giảm độ đậm.
- `frontend/src/styles/landing.css`: viết lại toàn bộ theo kích thước Figma ở 1440 px (container 1280, nav 100,
  H1 72/82, H2 60/68, H4 32/40, H5 24/32, Readex 16–18, bo 12/14/20/24) + responsive 360/480/640/900/1100/1200.
- Font: `@fontsource/readex-pro@5.3.0` (đúng font thiết kế), `@fontsource/playfair-display@5.3.0` thay "PP Editorial
  New" (thương mại, thiếu dấu tiếng Việt). Đã so 3 ứng viên serif có subset tiếng Việt: Newsreader và Fraunces đặt
  sai dấu chồng ("chế"), Playfair hiển thị đúng. Nạp trong `src/landing/fonts.js` (chunk landing/auth, không vào
  chunk chat).

### S-02 — claude-agent (component landing)

- `src/landing/LandingPage.jsx` (bố cục), `HeroComposer.jsx`, `FeatureBento.jsx`, `StepsCarousel.jsx`,
  `FaqList.jsx`, `content.js` (toàn bộ câu chữ), `fonts.js`.
- Thay nội dung không trung thực của bộ kit: dải logo đối tác → dải chủ đề; lời chứng thực → carousel 4 bước "Cách
  hoạt động"; thẻ "Advanced Voice"/"Choose your model"/"Collaborate and code" → trích dẫn/ngữ cảnh/lịch sử; FAQ 6
  câu thật (gồm giới hạn và việc quản trị viên xem được hội thoại). Lưu ý "có thể trả lời sai… đối chiếu văn bản
  gốc" luôn hiển thị dưới tiêu đề FAQ.

### S-03 — claude-agent (`/chat?q=`, trang tài khoản)

- `src/lib/appRoute.js`: `chatPathWithQuestion`, `readQuestionParam`, `QUESTION_PARAM_MAX_LENGTH = 1000`.
- `src/App.jsx`: đọc `q` một lần, truyền `initialInput` cho `ChatView`, xoá `q` khỏi URL bằng `replaceState`.
- `src/ChatView.jsx`: prop `initialInput` làm giá trị đầu của ô nhập, focus + đặt con trỏ cuối; không tự gửi.
- `src/auth/AuthLayout.jsx`, `src/styles/auth.css`: logo `.lp-brand`, font Readex/Playfair, thẻ nền gradient, nút
  tối, vòng focus màu nhấn.

### S-04 — claude-agent (test, kiểm chứng)

- `src/landing/LandingPage.test.jsx` (8 test), `src/App.test.jsx` (+1), `src/lib/appRoute.test.js` (+2).
- Kết quả: xem `verification.md`.

## Trao đổi giữa agents

- Không có (một agent).

## Bàn giao

- Lúc: `2026-10-28T09:25:00+07:00`; từ `claude-agent` tới người dùng.
- Thay đổi giao diện dùng chung: `ChatView` thêm prop `initialInput`; route `/chat` nhận `?q=`.
- Kiểm tra: V-01 … V-05 `passed`.
- Chưa làm: xem `review.md` R-01 … R-03 (không bắt buộc).

# Verification: 2026-10-28-landing-motion

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree của `feat/landing-motion` trước commit (`2026-10-28T21:07:39+07:00`).
- Môi trường: Linux container, Node v22, Vite 5 `vite preview` (bản build production), Chromium headless qua
  Playwright 1.63.0. Backend không chạy (landing coi lỗi `/auth/me` là khách).

## Kiểm chứng tiêu chí

### V-01 — AC-01 (đủ 9 nhóm hiệu ứng)

- Thao tác: script Playwright mở `/` ở 1280 × 800, chụp giữa/sau intro, di chuột trong hero, cuộn tới bento, hover
  thẻ, cuộn lên/xuống, cuộn qua dải kêu gọi, đổi bước carousel, mở FAQ, bấm CTA.
- Kết quả:
  1. Intro: ở 250 ms các từ `h1` đang trượt lên trong mặt nạ (`evidence/01-hero-intro-mid-1280.jpg`), sau ~2 s đủ
     tiêu đề, mô tả, CTA, khung soạn, hai thẻ nghiêng (`02-hero-intro-done-1280.jpg`).
  2. Tiêu đề section lộ theo từ, mô tả fade-up khi cuộn tới.
  3. Bento: `--progress` của thẻ rộng `1.0000`, hai thẻ kế `0.6188` đang lật (`03-bento-flip-in-progress-1280.jpg`);
     hover góc phải trên → `--rx: 2.13deg`, `--ry: 2.46deg`, `is-tilting` (`04-card-tilt-1280.jpg`); nhãn phạm vi
     rơi vào chỗ (`09-scope-tags-dark-1280.jpg`).
  4. Vòng chủ đề 3D xoay theo cuộn, thẻ sau mờ và nằm sau tiêu đề (`08-topic-ring-dark-1280.jpg`,
     `10-topic-ring-360.jpg`).
  5. Marquee dải chủ đề chạy (bản sao `aria-hidden`); chữ nền hero sáng dần theo cuộn.
  6. Nav: `top` ở đầu trang → `hidden` khi cuộn xuống → `scrolled` (viên thuốc kính mờ) khi cuộn lên 200 px
     (`05-nav-pill-1280.jpg`); khi đang `hidden`, focus vào "Đăng nhập" → `scrolled`, `top = 0`.
  7. Nút: sóng pulse trên mũi tên carousel (`06-carousel-step-change-1280.jpg`), nút hút theo chuột.
  8. Pixel transition ở 380 ms sau click (`07-pixel-transition-1280.jpg`), sau đó URL `/chat`.
  9. Parallax hero: hai thẻ nghiêng dịch theo chuột (so `01`/`02` với ảnh chụp sau khi di chuột).
- Phát hiện và sửa trong lúc kiểm: tiến độ lật bị kẹt ~0.02 do đo bằng `getBoundingClientRect` (R-02); vòng chủ đề
  ban đầu chỉ thấy nửa trước và thẻ sau đè lên tiêu đề (đổi sang billboard + mờ theo `cos()` + quỹ đạo nghiêng
  −26°/−58°); bóng nav còn lộ ở mép trên khi ẩn (đẩy −170 %).
- Trạng thái: `passed`.

### V-02 — AC-02 (giảm chuyển động)

- Thao tác: Playwright `reducedMotion: "reduce"`, mở `/`, bấm CTA. Test `motion.test.jsx` "người dùng giảm chuyển
  động", "tắt chuyển động thì chuyển trang ngay".
- Kết quả: không có `.motion-ready`, `document.getAnimations().length = 0`, 0 phần tử `data-reveal` có opacity khác 1,
  nav `position: relative` như trước; bấm CTA tới `/chat` sau 55 ms, không có `.lp-pixels`
  (`evidence/11-reduced-motion-1280.jpg`). CSS còn khối `@media (prefers-reduced-motion: reduce)` tắt animation/
  transition nếu người dùng bật giữa chừng.
- Trạng thái: `passed`.

### V-03 — AC-03 (không JS motion / không IO; text không đổi)

- Lệnh: `cd frontend && npx vitest run src/landing`.
- Kết quả: test "không có matchMedia (jsdom)…" (không `.motion-ready`), "thiếu IntersectionObserver: mọi data-reveal
  hiện ngay", "SplitWords … giữ nguyên textContent"; 8 test sẵn có của `LandingPage.test.jsx` giữ nguyên kỳ vọng
  (textContent `h2` "Hiểu câu hỏi tiếng ViệtChatbot giúp được gì", một `h1`, landmark, CTA, khung soạn, carousel,
  FAQ) và đều đạt. Trình duyệt: `h1.textContent = "Hỏi đáp quy chế PTITnhanh, có trích dẫn nguồn"` như trước.
- Trạng thái: `passed`.

### V-04 — AC-04 (chặn click đúng phạm vi, bfcache)

- Test: `shouldIntercept` (meta/ctrl/shift/alt, chuột giữa, `target=_blank`, khác origin → không chặn); click link
  `data-transition` với Ctrl → `defaultPrevented = false`, không lớp phủ; click thường → chặn, có lớp phủ + pulse,
  `goTo("/chat")` sau 700 ms (fake timers); `pageshow.persisted` gỡ lớp phủ; gọi lặp không tạo lớp phủ thứ hai.
- Trình duyệt: Ctrl/Meta/Shift + click CTA → `defaultPrevented` `[false, false, false]`, không `.lp-pixels`; click
  thường → `/chat`; Back → landing không còn `.lp-pixels`.
- Test landing: mọi `a[href^="/"]` (trừ `/`) có `data-transition`, link neo `#…` thì không — test này bắt được link
  "Đăng nhập" trong dòng ghi chú hero bị sót (R-01).
- Trạng thái: `passed`.

### V-05 — AC-05 (responsive, nav không che tiêu đề)

- Thao tác: Playwright 360/768/1280 × sáng/tối, cuộn suốt trang theo bước 400 px rồi đo.
- Kết quả: `scrollWidth == innerWidth` ở cả 6 tổ hợp. Bấm link nav "Câu hỏi thường gặp": `#cau-hoi` dừng ở
  `top = 96 px` (`scroll-margin-top`), nav viên thuốc cao 64 px + lề 10 px nên không che.
- Trạng thái: `passed`.

### V-06 — AC-06 (test, build, bundle)

- Lệnh (thư mục `frontend/`): `npx vitest run`, `npm run build`, `npm run check:bundle`.
- Kết quả: `Test Files 20 passed (20)`, `Tests 156 passed (156)` (trước task: 19 file, 146 test); build thành công;
  `check:bundle đạt.`
- Kích thước JS tải ban đầu của landing (gzip): `dev` `6e3cbf0` 73.47 kB (chunk `LandingPage` 7.33 kB) → nhánh này
  76.64 kB (chunk `LandingPage` 10.30 kB), +3.17 kB. CSS chung `index-*.css` gzip 20 157 B → 22 881 B (+2.7 kB).
  Trang chat 80.05 kB, dưới mốc FE-06 128.41 kB.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lỗi phát hiện và đã kiểm lại: R-01 (link sót `data-transition`), R-02 (vòng phản hồi tiến độ lật) — chạy lại
  V-01, V-04, V-06 sau khi sửa, đều đạt.
- Chưa kiểm: Safari và Firefox thật (chỉ Chromium); thiết bị cảm ứng thật (chỉ giả lập `isMobile/hasTouch` ở 360 px);
  đo FPS/hiệu năng trên máy yếu. `mask-composite`, `@property`, `cos()` có fallback (mất hiệu ứng phụ, nội dung vẫn
  hiện) nhưng chưa chạy thử trên trình duyệt thiếu các tính năng này.

## Kết luận

- Tiêu chí đã đạt: AC-01 … AC-06.
- Tiêu chí chưa đạt/chưa xác minh: không (giới hạn môi trường ghi ở trên).
- Đề xuất: bàn giao review.

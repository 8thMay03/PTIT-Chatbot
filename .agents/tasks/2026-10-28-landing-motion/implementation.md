# Implementation: 2026-10-28-landing-motion

## Tổng quan triển khai

Nhánh `feat/landing-motion` (tách từ `dev` tại `6e3cbf0`). S-01 … S-04 đã tích hợp trên cùng nhánh; không có phần
chờ. Không thêm dependency: toàn bộ chuyển động tự viết (IntersectionObserver + một vòng `requestAnimationFrame` ghi
biến CSS, CSS vẽ bằng transform/opacity).

Bản đồ hiệu ứng tham chiếu → landing:

| Hiệu ứng của eduardbodak.com (theo mô tả công khai) | Áp dụng trên landing |
|---|---|
| Thẻ lật 3D khi cuộn | 5 thẻ bento lật `rotateX` (+ `rotateY` xen kẽ) theo tiến độ cuộn, minh hoạ bên trong chạy so le khi thẻ vào khung nhìn (nhãn phạm vi rơi và nảy, chip trích dẫn trượt vào, bong bóng chat hiện lần lượt) |
| Thẻ tương tác nghiêng theo chuột | Thẻ bento và carousel nghiêng theo con trỏ, vệt sáng (glare) theo vị trí chuột |
| Bố cục thẻ vòng tròn xoay theo cuộn | Vòng 10 thẻ chủ đề 3D (`TopicRing`) quanh tiêu đề dải kêu gọi, xoay theo cuộn, thẻ luôn quay mặt về người xem, mờ dần theo độ sâu |
| Micro-animation điều hướng | Nav cố định, thu thành viên thuốc kính mờ khi cuộn, ẩn khi cuộn xuống/hiện khi cuộn lên hoặc khi focus; link cuộn chữ khi hover; logo xoay nhẹ |
| Pulse khi click | Vòng sóng tại điểm click trên nút chính, chip, nút gửi, mũi tên carousel; nút nhún khi nhấn |
| Pixel transition | Lưới ô maroon phủ màn hình (lan chéo + nhiễu) trước khi chuyển sang `/chat`, `/login`, `/register` |
| Chữ lộ theo dòng/từ | Tiêu đề `h1`/`h2` trượt lên theo từng từ trong mặt nạ; đoạn mô tả, CTA, khung soạn fade-up so le; quote carousel trượt vào lại khi đổi bước |
| Parallax/marquee | Haze, chữ nền và hai thẻ nghiêng hero trôi theo cuộn/chuột, thẻ nghiêng lơ lửng; dải chủ đề chạy marquee vô hạn (dừng khi hover); chữ nền hero sáng dần từng dòng theo cuộn; viền gradient xoay quanh khung soạn khi hover/gõ |

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-10-28T21:07:39+07:00`.
- Đã làm: thư mục mới `frontend/src/landing/motion/`:
  - `env.js` — `motionEnabled()` (cần `matchMedia` và không `prefers-reduced-motion: reduce`), `canHover()`, `clamp01`.
  - `SplitWords.jsx` — tách từ, khoảng trắng là text node nên `textContent`/tên truy cập không đổi; `--i` là thứ tự.
  - `pixelTransition.js` — `transitionTo(url)` (tắt chuyển động → `goTo` ngay), lớp phủ gắn vào `body`, gỡ ở
    `pageshow.persisted` (bfcache) và failsafe 4 s; `shouldIntercept(event, anchor)` chỉ nhận click trái không phím
    bổ trợ, cùng origin, không `target`/`download`.
  - `useLandingMotion.js` — layout effect gắn `.motion-ready`; reveal (IO, thiếu IO → hiện hết), scrub `--progress`,
    trạng thái nav có trễ (ẩn sau 64 px cuộn xuống, hiện sau 24 px cuộn lên, không ẩn khi focus trong nav), con trỏ
    (tilt/magnetic/parallax hero, chỉ khi `hover: hover`), click (pulse + pixel transition). Gỡ mọi listener khi
    unmount.
- Quyết định: đo `--progress` bằng `offsetTop`/`offsetHeight` thay vì `getBoundingClientRect` — bản đầu dùng rect,
  transform của chính thẻ lật kéo tiến độ về ~0.02 (vòng phản hồi, phát hiện ở V-01, xem R-02).
- File: `frontend/src/landing/motion/{env.js,SplitWords.jsx,pixelTransition.js,useLandingMotion.js}`.

### S-02 — claude-agent

- Cập nhật lúc: `2026-10-28T21:07:39+07:00`.
- Đã làm: `LandingPage.jsx` (`DisplayLines`, `RollLink`, `TopicMarquee`, `PrimaryLink` có
  `data-magnetic/pulse/transition`, mọi link nội bộ sang trang khác có `data-transition`), `HeroComposer.jsx` (gửi
  qua `transitionTo`, viền glow), `FeatureBento.jsx` (`Card` với `data-scrub="enter"`, `data-tilt`, glare),
  `StepsCarousel.jsx` (`key` theo bước để chữ trượt vào lại, tilt nhẹ `0.35`), `FaqList.jsx` (reveal so le),
  `TopicRing.jsx` (mới), `content.js` (thêm `RING_TOPICS`, không đổi câu chữ hiện có).
- Quyết định: bỏ chữ nền mờ ở dải kêu gọi, thay bằng vòng chủ đề 3D (hai lớp trang trí chồng nhau quá rối); chữ nền
  hero giữ nguyên và sáng dần theo cuộn.

### S-03 — claude-agent

- Cập nhật lúc: `2026-10-28T21:07:39+07:00`.
- Đã làm: `frontend/src/styles/landing-motion.css` (mới, import sau `landing.css`); `tokens.css` thêm `--lp-glare`,
  `--lp-pixel`, `--lp-nav-glass` (sáng + hai khối tối); `landing.css` đổi `.lp-hero-copy > .lp-btn` thành
  `.lp-hero-cta`, bỏ rule chữ nền dải kêu gọi. Gradient tiêu đề chuyển từ dòng xuống từng từ (`.has-words`) để
  `background-clip: text` không vỡ khi từ có transform. Màn < 640 px: quỹ đạo vòng dựng đứng hơn, thẻ nhỏ hơn.
- `README.md`: một đoạn mô tả chuyển động và hành vi giảm chuyển động ở mục bảng đường dẫn.

### S-04 — claude-agent

- Cập nhật lúc: `2026-10-28T21:07:39+07:00`.
- Đã làm: `frontend/src/landing/motion/motion.test.jsx` (9 test), thêm 1 test trong `LandingPage.test.jsx`; script
  Playwright ngoài repo (scratchpad phiên) chụp khung hình và đo — kết quả trong `verification.md`, ảnh trong
  `evidence/`.

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

### HANDOFF-claude-agent-001 — S-01 … S-04

- Từ / đến: `claude-agent` / người dùng.
- Đã hoàn tất: 9 nhóm hiệu ứng theo `task.md`, test, kiểm chứng trình duyệt, self-review.
- File/branch/commit: nhánh `feat/landing-motion`, merge vào `dev` theo yêu cầu phiên (xem lịch sử git).
- Kiểm chứng: `verification.md` V-01 … V-06 `passed`.
- Review: `review.md` `self_review` `approved`; R-03, R-04 `deferred` (không bắt buộc).
- Hạn chế: trang tham chiếu bị chặn mạng nên bộ hiệu ứng là diễn giải từ mô tả công khai, không đối chiếu từng khung
  hình; chưa kiểm trên Safari/Firefox thật (chỉ Chromium headless).
- Bước tiếp theo: người dùng xem landing; muốn bám sát hơn thì cho phép tên miền `www.eduardbodak.com` trong cài đặt
  mạng của phiên để đối chiếu.

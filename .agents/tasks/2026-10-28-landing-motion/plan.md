# Plan: 2026-10-28-landing-motion

Nền: `dev` tại `6e3cbf0` (landing Figma đã merge). Một agent (`claude-agent`) làm tuần tự trên nhánh
`feat/landing-motion`.

## Phân công

### S-01 — Lõi chuyển động (`frontend/src/landing/motion/`)

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu:
  - `prefersReducedMotion()`, `canHover()` an toàn khi thiếu `matchMedia`.
  - `useLandingMotion(rootRef)`: một vòng `requestAnimationFrame` duy nhất theo cuộn/chuột, cập nhật biến CSS:
    - `[data-reveal]` → thêm `is-revealed` khi vào khung nhìn (IntersectionObserver, một lần). Thiếu IO hoặc
      reduced motion → hiện ngay.
    - `[data-scrub]` → `--progress` 0…1 theo vị trí phần tử đi qua khung nhìn.
    - Nav: `data-nav-state` = `top | scrolled | hidden`.
    - `[data-magnetic]` → `--mx/--my`; `[data-tilt]` → `--rx/--ry/--gx/--gy` (chỉ con trỏ hover được).
    - Hero: `--hero-px/--hero-py` theo chuột, `--scroll-y`.
    - Pulse khi click `[data-pulse]`.
  - `SplitWords`: tách chữ thành từ trong mặt nạ, giữ nguyên `textContent` (khoảng trắng là text node).
  - `PixelTransition` + `transitionTo(url)`: lưới ô phủ màn hình rồi `goTo`; bỏ qua khi reduced motion; gỡ
    lớp phủ ở `pageshow` (bfcache).
  Phục vụ `AC-01` … `AC-04`.
- Phạm vi file: `frontend/src/landing/motion/*` (mới).
- Phụ thuộc: không.

### S-02 — Gắn hiệu ứng vào các khối landing

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: hero (intro từ, haze/thẻ parallax, composer tilt), nav (dính + link cuộn chữ), dải chủ đề marquee,
  tiêu đề section `SplitWords`, bento lật 3D + tilt, carousel đổi bước có chuyển cảnh, FAQ mở có chuyển cảnh,
  CTA vòng thẻ 3D xoay theo cuộn + nền chữ tô sáng theo cuộn, CTA nội bộ dùng pixel transition.
  Phục vụ `AC-01`, `AC-04`, `AC-05`.
- Phạm vi file: `frontend/src/landing/{LandingPage,HeroComposer,FeatureBento,StepsCarousel,FaqList}.jsx`,
  `frontend/src/landing/TopicRing.jsx` (mới), `frontend/src/landing/content.js` (chỉ thêm dữ liệu vòng thẻ
  nếu cần, không đổi câu chữ).
- Phụ thuộc: S-01.

### S-03 — CSS chuyển động

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `frontend/src/styles/landing-motion.css` (mới, import sau `landing.css`): keyframes, trạng thái
  reveal, transform theo biến CSS, khối `@media (prefers-reduced-motion: reduce)` tắt toàn bộ; nav dính và
  `scroll-margin-top` cho section. Chỉnh `landing.css` tối thiểu khi cần (nav `position`).
  Phục vụ `AC-01`, `AC-02`, `AC-05`.
- Phạm vi file: `frontend/src/styles/landing-motion.css`, `frontend/src/styles/landing.css`,
  `frontend/src/styles/index.css` (chỉ thêm import).
- Phụ thuộc: S-02 (tên class).

### S-04 — Test và kiểm chứng

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: test `motion` (SplitWords giữ text, reveal fallback, transition bỏ qua phím bổ trợ/reduced
  motion); chạy `npm test`, `npm run build`, `npm run check:bundle`; Playwright chụp ảnh khung hình chuyển
  động, kiểm cuộn ngang 360/768/1280 sáng/tối, reduced motion.
  Phục vụ `AC-02` … `AC-06`.
- Phạm vi file: `frontend/src/landing/motion/*.test.jsx`, `frontend/src/landing/LandingPage.test.jsx`.
- Phụ thuộc: S-01 … S-03.

## Hợp đồng dùng chung

- Không đổi API/route. `goTo` trong `frontend/src/lib/appRoute.js` giữ nguyên; `transitionTo(url)` gọi `goTo`
  sau hiệu ứng nên test hiện có (mock `goTo`) vẫn áp dụng.
- Thuộc tính dữ liệu: `data-reveal` (`up | words | flip | fade`), `data-scrub`, `data-magnetic`, `data-tilt`,
  `data-pulse`, `data-transition` (trên `<a>` nội bộ), `data-nav-state` (trên `.lp-nav`).
- Năm file task: coordinator `claude-agent` ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: AC-01 … AC-06.
- Reviewer: `claude-agent`; hình thức `self_review` (không có agent khác trong phiên).
- Trọng tâm review: hiệu năng (một vòng rAF, không layout thrash, `will-change` có chừng mực), a11y (reduced
  motion, text không đổi, focus không bị che bởi nav), không chặn điều hướng/tab mới, rò rỉ listener khi unmount.

## Thứ tự tích hợp và kiểm chứng

1. S-01 → S-02 → S-03 trên cùng nhánh.
2. S-04: test tự động rồi kiểm tra trên trình duyệt (Playwright, `vite preview`).
3. Self-review, sửa `R-*` bắt buộc, chạy lại kiểm tra bị ảnh hưởng.
4. Commit trên `feat/landing-motion`; merge vào `dev` theo yêu cầu của phiên.

## Rủi ro và điều chỉnh kế hoạch

- Không xem được trang tham chiếu → bộ hiệu ứng là diễn giải; ghi rõ trong bàn giao để người dùng chỉnh nếu
  muốn giống hơn (ví dụ cho phép tên miền trong cài đặt mạng của phiên).
- Hiệu ứng 3D/tilt trên máy yếu → chỉ cập nhật biến CSS trong rAF, transform/opacity thuần, tắt tilt khi không
  có con trỏ hover.

import { useLayoutEffect } from "react";
import { clamp01, motionEnabled } from "../../lib/motion/env";
import { setupClicks, setupPointer, setVars } from "../../lib/motion/interactions";

/**
 * Bộ chuyển động của trang landing, gắn một lần lên phần tử gốc. Không thư viện:
 * IntersectionObserver cho reveal, một vòng `requestAnimationFrame` cho mọi hiệu
 * ứng theo cuộn/chuột, kết quả ghi vào biến CSS để CSS tự vẽ (transform/opacity).
 *
 * Thuộc tính dữ liệu (xem landing-motion.css; tilt/magnetic/pulse/transition ở
 * `lib/motion/interactions.js`):
 * - `data-reveal`  thêm `is-revealed` khi vào khung nhìn (một lần).
 * - `data-scrub`   `--progress` 0…1: `enter` = từ khi mép trên chạm đáy tới 60%
 *                  chiều cao khung nhìn; mặc định = suốt quãng phần tử đi qua.
 * - `.lp-nav` nhận `data-nav-state` = top | scrolled | hidden.
 * - `.lp-hero` nhận `--scroll-y` (px) và `--hero-px/--hero-py` (-0.5…0.5).
 *
 * Tắt chuyển động (xem env.js) thì không làm gì: CSS chỉ ẩn phần tử chờ reveal
 * dưới `.motion-ready`, nên nội dung luôn hiện.
 */

const NAV_SOLID_AFTER = 24;
const NAV_HIDE_AFTER = 480;
const NAV_HIDE_DELTA = 64;
const NAV_SHOW_DELTA = 24;

/**
 * Vị trí layout trong tài liệu, bỏ qua transform. Không dùng getBoundingClientRect
 * cho phần tử `data-scrub` vì transform do chính `--progress` sinh ra (thẻ lật trượt
 * xuống) sẽ kéo tiến độ về 0 — vòng phản hồi.
 */
function layoutTop(element) {
  let top = 0;
  for (let node = element; node; node = node.offsetParent) top += node.offsetTop;
  return top;
}

function setupReveal(root) {
  const targets = root.querySelectorAll("[data-reveal]");
  if (typeof IntersectionObserver !== "function") {
    targets.forEach((element) => element.classList.add("is-revealed"));
    return () => {};
  }
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("is-revealed");
        observer.unobserve(entry.target);
      }
    },
    { rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
  );
  targets.forEach((element) => observer.observe(element));
  return () => observer.disconnect();
}

function setupScroll(root) {
  const scrubbed = [...root.querySelectorAll("[data-scrub]")];
  const nav = root.querySelector(".lp-nav");
  const hero = root.querySelector(".lp-hero");
  let frame = 0;
  let navState = "";
  let navHidden = false;
  let anchorY = window.scrollY;

  function updateNav(y) {
    if (!nav) return;
    if (y < NAV_HIDE_AFTER || nav.contains(document.activeElement)) {
      navHidden = false;
      anchorY = y;
    } else if (navHidden) {
      if (y > anchorY) anchorY = y;
      else if (anchorY - y > NAV_SHOW_DELTA) {
        navHidden = false;
        anchorY = y;
      }
    } else if (y < anchorY) anchorY = y;
    else if (y - anchorY > NAV_HIDE_DELTA) {
      navHidden = true;
      anchorY = y;
    }
    const next = navHidden ? "hidden" : y > NAV_SOLID_AFTER ? "scrolled" : "top";
    if (next !== navState) {
      navState = next;
      nav.dataset.navState = next;
    }
  }

  function update() {
    frame = 0;
    const y = window.scrollY;
    const viewport = window.innerHeight || 1;
    // Đọc hết vị trí trước rồi mới ghi biến CSS để không ép trình duyệt tính lại layout.
    const values = scrubbed.map((element) => {
      const top = layoutTop(element) - y;
      const height = element.offsetHeight;
      if (top + height < 0 || top > viewport) return null;
      const progress =
        element.dataset.scrub === "enter"
          ? (viewport - top) / (viewport * 0.4)
          : (viewport - top) / (viewport + height);
      return clamp01(progress).toFixed(4);
    });
    values.forEach((value, index) => {
      if (value !== null) scrubbed[index].style.setProperty("--progress", value);
    });
    if (hero && y < viewport * 2) hero.style.setProperty("--scroll-y", `${Math.round(y)}`);
    updateNav(y);
  }

  const schedule = () => {
    if (!frame) frame = window.requestAnimationFrame(update);
  };
  const showNav = () => {
    navHidden = false;
    schedule();
  };

  window.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", schedule);
  nav?.addEventListener("focusin", showNav);
  update();

  return () => {
    window.cancelAnimationFrame(frame);
    window.removeEventListener("scroll", schedule);
    window.removeEventListener("resize", schedule);
    nav?.removeEventListener("focusin", showNav);
    nav?.removeAttribute("data-nav-state");
  };
}

/** Parallax hero theo chuột: `--hero-px/--hero-py` trong -0.5…0.5. */
function moveHero(hero, event, target) {
  if (!hero || !hero.contains(target)) return;
  const rect = hero.getBoundingClientRect();
  setVars(hero, {
    "--hero-px": ((event.clientX - rect.left) / rect.width - 0.5).toFixed(3),
    "--hero-py": ((event.clientY - rect.top) / rect.height - 0.5).toFixed(3),
  });
}

export default function useLandingMotion(rootRef) {
  // Layout effect: gắn `.motion-ready` trước lần vẽ đầu nên phần tử chờ reveal
  // không nháy hiện rồi mới ẩn.
  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root || !motionEnabled()) return undefined;
    root.classList.add("motion-ready");
    const hero = root.querySelector(".lp-hero");
    const cleanups = [
      setupReveal(root),
      setupScroll(root),
      setupPointer(root, { onMove: (event, target) => moveHero(hero, event, target) }),
      setupClicks(root),
    ];
    return () => {
      cleanups.forEach((cleanup) => cleanup());
      root.classList.remove("motion-ready");
    };
  }, [rootRef]);
}

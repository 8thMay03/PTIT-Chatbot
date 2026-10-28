import { useLayoutEffect } from "react";
import { canHover, clamp01, motionEnabled } from "./env";
import { shouldIntercept, transitionTo } from "./pixelTransition";

/**
 * Bộ chuyển động của trang landing, gắn một lần lên phần tử gốc. Không thư viện:
 * IntersectionObserver cho reveal, một vòng `requestAnimationFrame` cho mọi hiệu
 * ứng theo cuộn/chuột, kết quả ghi vào biến CSS để CSS tự vẽ (transform/opacity).
 *
 * Thuộc tính dữ liệu (xem landing-motion.css):
 * - `data-reveal`  thêm `is-revealed` khi vào khung nhìn (một lần).
 * - `data-scrub`   `--progress` 0…1: `enter` = từ khi mép trên chạm đáy tới 60%
 *                  chiều cao khung nhìn; mặc định = suốt quãng phần tử đi qua.
 * - `data-tilt`    `--rx/--ry` (độ) và `--gx/--gy` (vị trí vệt sáng) theo chuột;
 *                  giá trị số (ví dụ `0.4`) là hệ số độ nghiêng.
 * - `data-magnetic` `--mx/--my` (px) hút theo chuột.
 * - `data-pulse`   vòng sóng tại điểm click.
 * - `a[data-transition]` chuyển trang qua pixel transition.
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
const TILT_DEG = 7;
const MAGNET = 0.28;

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

function setVars(element, vars) {
  for (const [name, value] of Object.entries(vars)) element.style.setProperty(name, value);
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

function setupPointer(root) {
  if (!canHover()) return () => {};
  const hero = root.querySelector(".lp-hero");
  const magnetOffset = new WeakMap();
  let tiltTarget = null;
  let magnetTarget = null;
  let lastEvent = null;
  let frame = 0;

  function resetTilt(element) {
    setVars(element, { "--rx": "0deg", "--ry": "0deg" });
    element.classList.remove("is-tilting");
  }

  function resetMagnet(element) {
    magnetOffset.set(element, { x: 0, y: 0 });
    setVars(element, { "--mx": "0px", "--my": "0px" });
  }

  function update() {
    frame = 0;
    const event = lastEvent;
    if (!event) return;
    const target = event.target instanceof Element ? event.target : null;

    const tilt = target?.closest("[data-tilt]") ?? null;
    if (tilt !== tiltTarget) {
      if (tiltTarget) resetTilt(tiltTarget);
      tiltTarget = tilt;
    }
    if (tilt) {
      const rect = tilt.getBoundingClientRect();
      const px = (event.clientX - rect.left) / rect.width;
      const py = (event.clientY - rect.top) / rect.height;
      const degrees = TILT_DEG * (Number(tilt.dataset.tilt) || 1);
      tilt.classList.add("is-tilting");
      setVars(tilt, {
        "--rx": `${((0.5 - py) * degrees).toFixed(2)}deg`,
        "--ry": `${((px - 0.5) * degrees).toFixed(2)}deg`,
        "--gx": `${(px * 100).toFixed(1)}%`,
        "--gy": `${(py * 100).toFixed(1)}%`,
      });
    }

    const magnet = target?.closest("[data-magnetic]") ?? null;
    if (magnet !== magnetTarget) {
      if (magnetTarget) resetMagnet(magnetTarget);
      magnetTarget = magnet;
    }
    if (magnet) {
      // Trừ phần đã dịch để tâm nút là tâm gốc, tránh dao động phản hồi.
      const offset = magnetOffset.get(magnet) ?? { x: 0, y: 0 };
      const rect = magnet.getBoundingClientRect();
      const cx = rect.left - offset.x + rect.width / 2;
      const cy = rect.top - offset.y + rect.height / 2;
      const next = { x: (event.clientX - cx) * MAGNET, y: (event.clientY - cy) * MAGNET };
      magnetOffset.set(magnet, next);
      setVars(magnet, { "--mx": `${next.x.toFixed(1)}px`, "--my": `${next.y.toFixed(1)}px` });
    }

    if (hero && hero.contains(target)) {
      const rect = hero.getBoundingClientRect();
      setVars(hero, {
        "--hero-px": ((event.clientX - rect.left) / rect.width - 0.5).toFixed(3),
        "--hero-py": ((event.clientY - rect.top) / rect.height - 0.5).toFixed(3),
      });
    }
  }

  function handleMove(event) {
    lastEvent = event;
    if (!frame) frame = window.requestAnimationFrame(update);
  }

  function handleLeave() {
    lastEvent = null;
    if (tiltTarget) resetTilt(tiltTarget);
    if (magnetTarget) resetMagnet(magnetTarget);
    tiltTarget = null;
    magnetTarget = null;
  }

  root.addEventListener("pointermove", handleMove, { passive: true });
  root.addEventListener("pointerleave", handleLeave);
  return () => {
    window.cancelAnimationFrame(frame);
    root.removeEventListener("pointermove", handleMove);
    root.removeEventListener("pointerleave", handleLeave);
  };
}

function setupClicks(root) {
  function handleClick(event) {
    const target = event.target instanceof Element ? event.target : null;
    const pulseHost = target?.closest("[data-pulse]");
    if (pulseHost) {
      const rect = pulseHost.getBoundingClientRect();
      // Click bằng bàn phím (detail = 0) không có toạ độ chuột → sóng từ tâm.
      const fromPointer = event.detail > 0;
      const pulse = document.createElement("span");
      pulse.className = "lp-pulse";
      pulse.setAttribute("aria-hidden", "true");
      pulse.style.left = `${fromPointer ? event.clientX - rect.left : rect.width / 2}px`;
      pulse.style.top = `${fromPointer ? event.clientY - rect.top : rect.height / 2}px`;
      pulseHost.append(pulse);
      const remove = () => pulse.remove();
      pulse.addEventListener("animationend", remove, { once: true });
      window.setTimeout(remove, 1200);
    }

    const anchor = target?.closest("a[data-transition]");
    if (anchor && shouldIntercept(event, anchor)) {
      event.preventDefault();
      transitionTo(anchor.getAttribute("href"));
    }
  }

  root.addEventListener("click", handleClick);
  return () => root.removeEventListener("click", handleClick);
}

export default function useLandingMotion(rootRef) {
  // Layout effect: gắn `.motion-ready` trước lần vẽ đầu nên phần tử chờ reveal
  // không nháy hiện rồi mới ẩn.
  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root || !motionEnabled()) return undefined;
    root.classList.add("motion-ready");
    const cleanups = [setupReveal(root), setupScroll(root), setupPointer(root), setupClicks(root)];
    return () => {
      cleanups.forEach((cleanup) => cleanup());
      root.classList.remove("motion-ready");
    };
  }, [rootRef]);
}

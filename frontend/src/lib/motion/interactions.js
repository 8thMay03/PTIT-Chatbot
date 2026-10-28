import { canHover } from "./env";
import { shouldIntercept, transitionTo } from "./pixelTransition";

/**
 * Tương tác con trỏ/click dùng chung cho landing và trang chat. Gắn lên phần tử
 * gốc, uỷ quyền theo thuộc tính dữ liệu (CSS vẽ từ biến được ghi):
 * - `data-tilt`     `--rx/--ry` (độ) và `--gx/--gy` (vị trí vệt sáng) theo chuột,
 *                   thêm `is-tilting`; giá trị số (ví dụ `0.4`) là hệ số độ nghiêng.
 * - `data-magnetic` `--mx/--my` (px) hút theo chuột.
 * - `data-pulse`    vòng sóng `.motion-pulse` tại điểm click.
 * - `a[data-transition]` chuyển trang qua pixel transition.
 * Người gọi tự kiểm `motionEnabled()` trước khi gắn.
 */

const TILT_DEG = 7;
const MAGNET = 0.28;

export function setVars(element, vars) {
  for (const [name, value] of Object.entries(vars)) element.style.setProperty(name, value);
}

export function setupPointer(root, { onMove } = {}) {
  if (!canHover()) return () => {};
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

    onMove?.(event, target);
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

export function setupClicks(root) {
  function handleClick(event) {
    const target = event.target instanceof Element ? event.target : null;
    const pulseHost = target?.closest("[data-pulse]");
    if (pulseHost) {
      const rect = pulseHost.getBoundingClientRect();
      // Click bằng bàn phím (detail = 0) không có toạ độ chuột → sóng từ tâm.
      const fromPointer = event.detail > 0;
      const pulse = document.createElement("span");
      pulse.className = "motion-pulse";
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

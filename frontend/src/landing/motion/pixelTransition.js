import { goTo } from "../../lib/appRoute";
import { motionEnabled } from "./env";

/**
 * Pixel transition khi rời landing: lưới ô vuông màu thương hiệu phủ dần màn hình
 * (lan chéo từ góc trên trái, có nhiễu ngẫu nhiên) rồi mới chuyển trang. Lớp phủ
 * gắn thẳng vào `document.body` để HeroComposer và link đều dùng chung.
 */

const CELL_PX = 72;
const COVER_MS = 620;
const FAILSAFE_MS = 4000;

let overlay = null;
let failsafe = null;

function removeOverlay() {
  window.clearTimeout(failsafe);
  overlay?.remove();
  overlay = null;
}

// Quay lại bằng Back (bfcache) thì trang được khôi phục nguyên trạng — gỡ lớp phủ.
function handlePageShow(event) {
  if (event.persisted) removeOverlay();
}

function buildOverlay() {
  const cols = Math.max(1, Math.ceil(window.innerWidth / CELL_PX));
  const rows = Math.max(1, Math.ceil(window.innerHeight / CELL_PX));
  const node = document.createElement("div");
  node.className = "lp-pixels";
  node.setAttribute("aria-hidden", "true");
  node.style.setProperty("--cols", cols);
  node.style.setProperty("--rows", rows);
  const fragment = document.createDocumentFragment();
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const cell = document.createElement("span");
      const diagonal = (col / cols + row / rows) / 2;
      cell.style.animationDelay = `${Math.round(diagonal * 300 + Math.random() * 200)}ms`;
      fragment.append(cell);
    }
  }
  node.append(fragment);
  return node;
}

export function transitionTo(url) {
  if (!motionEnabled()) {
    goTo(url);
    return;
  }
  if (overlay) return;
  overlay = buildOverlay();
  document.body.append(overlay);
  window.addEventListener("pageshow", handlePageShow);
  window.setTimeout(() => goTo(url), COVER_MS);
  // Điều hướng bị huỷ (beforeunload, lỗi mạng…) thì không để lớp phủ che trang mãi.
  failsafe = window.setTimeout(removeOverlay, FAILSAFE_MS);
}

/** Chỉ chặn click chuột trái thường; Ctrl/⌘/Shift/Alt hay chuột giữa mở tab mới như cũ. */
export function shouldIntercept(event, anchor) {
  if (event.defaultPrevented || event.button !== 0) return false;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
  if (anchor.target && anchor.target !== "_self") return false;
  if (anchor.hasAttribute("download")) return false;
  return anchor.origin === window.location.origin;
}

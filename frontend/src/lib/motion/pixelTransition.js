import { goTo } from "../appRoute";
import { motionEnabled } from "./env";

/**
 * Pixel transition giữa các trang: khi rời trang, lưới ô vuông màu thương hiệu phủ
 * dần màn hình (lan chéo từ góc trên trái, có nhiễu ngẫu nhiên) rồi mới chuyển
 * trang; trang đích gọi `playPixelEnter()` lúc khởi động để lưới đó "tan ra".
 * Lớp phủ gắn thẳng vào `document.body`, dùng chung cho landing, chat và link.
 */

const CELL_PX = 72;
const COVER_MS = 620;
const FAILSAFE_MS = 4000;
const ENTER_MS = 900;
// Cờ cho trang đích: thời điểm rời trang. Quá hạn (điều hướng hỏng, mở lại tab
// sau) thì bỏ qua để không phát hiệu ứng vào trang lạc lõng.
const ENTER_FLAG = "ptit:pixel-enter";
const ENTER_FLAG_TTL_MS = 5000;

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

function buildOverlay(mode) {
  const cols = Math.max(1, Math.ceil(window.innerWidth / CELL_PX));
  const rows = Math.max(1, Math.ceil(window.innerHeight / CELL_PX));
  const node = document.createElement("div");
  node.className = `pixel-overlay is-${mode}`;
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

function writeEnterFlag() {
  try {
    window.sessionStorage.setItem(ENTER_FLAG, String(Date.now()));
  } catch {
    /* sessionStorage bị chặn: trang đích chỉ không có hiệu ứng vào trang */
  }
}

/** Đọc và xoá cờ; true khi trang trước vừa chạy pixel transition. */
function consumeEnterFlag() {
  try {
    const value = Number(window.sessionStorage.getItem(ENTER_FLAG));
    window.sessionStorage.removeItem(ENTER_FLAG);
    return value > 0 && Date.now() - value < ENTER_FLAG_TTL_MS;
  } catch {
    return false;
  }
}

export function transitionTo(url) {
  if (!motionEnabled()) {
    goTo(url);
    return;
  }
  if (overlay) return;
  overlay = buildOverlay("cover");
  document.body.append(overlay);
  window.addEventListener("pageshow", handlePageShow);
  window.setTimeout(() => {
    writeEnterFlag();
    goTo(url);
  }, COVER_MS);
  // Điều hướng bị huỷ (beforeunload, lỗi mạng…) thì không để lớp phủ che trang mãi.
  failsafe = window.setTimeout(removeOverlay, FAILSAFE_MS);
}

/**
 * Gọi một lần khi trang khởi động (trước khi React vẽ). Trang trước vừa chạy
 * pixel transition thì phủ lưới kín rồi cho từng ô biến mất; lớp phủ không chặn
 * thao tác (`pointer-events: none`) và tự gỡ sau khi tan.
 */
export function playPixelEnter() {
  if (typeof window === "undefined" || !consumeEnterFlag() || !motionEnabled()) return false;
  const node = buildOverlay("reveal");
  document.body.append(node);
  window.setTimeout(() => node.remove(), ENTER_MS);
  return true;
}

/** Chỉ chặn click chuột trái thường; Ctrl/⌘/Shift/Alt hay chuột giữa mở tab mới như cũ. */
export function shouldIntercept(event, anchor) {
  if (event.defaultPrevented || event.button !== 0) return false;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
  if (anchor.target && anchor.target !== "_self") return false;
  if (anchor.hasAttribute("download")) return false;
  return anchor.origin === window.location.origin;
}

import React, { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Brain, Check, ChevronDown } from "lucide-react";

export const REASONING_EFFORT_OPTIONS = [
  { value: "auto", label: "Tự động", description: "Mô hình tự chọn mức suy luận" },
  { value: "low", label: "Thấp", description: "Trả lời nhanh, suy luận ngắn" },
  { value: "medium", label: "Trung bình", description: "Cân bằng tốc độ và độ kỹ" },
  { value: "high", label: "Cao", description: "Suy luận kỹ, trả lời chậm hơn" },
];

/**
 * Nút chọn mức suy luận ("thinking effort") ở khung nhập chat; áp dụng từ câu hỏi
 * gửi tiếp theo. Model không hỗ trợ thì server bỏ qua tham số.
 *
 * Menu render qua portal vào `document.body` (giống `UserMenu`): hiệu ứng vào trang
 * của `.composer-shell` (`animation … both`) biến nó thành containing block, nên
 * menu `position: fixed` nằm trong đó sẽ bị lệch hoặc bị nội dung chat đè.
 */
export default function ReasoningEffortPicker({ value = "auto", onChange }) {
  const [open, setOpen] = useState(false);
  const [menuPosition, setMenuPosition] = useState(null);
  const menuRef = useRef(null);
  const triggerRef = useRef(null);
  const itemsRef = useRef([]);
  const menuId = `effort-menu-${useId().replace(/:/g, "")}`;
  const current =
    REASONING_EFFORT_OPTIONS.find((option) => option.value === value) ?? REASONING_EFFORT_OPTIONS[0];

  // Mở menu thì focus mức đang chọn; bấm ra ngoài hoặc đổi kích thước cửa sổ thì đóng.
  useEffect(() => {
    if (!open) return undefined;
    const selected = REASONING_EFFORT_OPTIONS.findIndex((option) => option.value === current.value);
    itemsRef.current[Math.max(selected, 0)]?.focus({ preventScroll: true });
    function onPointerDown(event) {
      if (!menuRef.current?.contains(event.target) && !triggerRef.current?.contains(event.target)) {
        setOpen(false);
      }
    }
    function onResize() {
      setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    window.addEventListener("resize", onResize);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("resize", onResize);
    };
  }, [open, current.value]);

  function closeMenu() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  /** Mở phía trên nút, mép phải thẳng nút; không tràn mép trái màn hình hẹp. */
  function toggleMenu() {
    if (open) {
      setOpen(false);
      return;
    }
    const rect = triggerRef.current.getBoundingClientRect();
    const width = Math.min(260, window.innerWidth - 24);
    setMenuPosition({
      left: Math.max(12, rect.right - width),
      bottom: window.innerHeight - rect.top + 8,
      width,
    });
    setOpen(true);
  }

  function choose(nextValue) {
    onChange?.(nextValue);
    closeMenu();
  }

  function onMenuKeyDown(event) {
    const items = itemsRef.current.filter(Boolean);
    const index = items.indexOf(document.activeElement);
    if (event.key === "Escape") {
      event.stopPropagation();
      closeMenu();
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      items[(index + step + items.length) % items.length]?.focus({ preventScroll: true });
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      items[event.key === "Home" ? 0 : items.length - 1]?.focus({ preventScroll: true });
    } else if (event.key === "Tab") {
      // Menu nằm cuối <body> (portal): Tab tiếp sẽ rời trang, nên trả focus về nút.
      event.preventDefault();
      closeMenu();
    }
  }

  const menu = open
    ? createPortal(
        <div
          ref={menuRef}
          className="effort-menu"
          id={menuId}
          role="menu"
          aria-label="Mức suy luận"
          style={menuPosition ?? undefined}
          onKeyDown={onMenuKeyDown}
        >
          <div className="effort-menu-head" aria-hidden="true">
            Mức suy luận
          </div>
          {REASONING_EFFORT_OPTIONS.map((option, index) => {
            const checked = option.value === current.value;
            return (
              <button
                key={option.value}
                ref={(node) => {
                  itemsRef.current[index] = node;
                }}
                type="button"
                role="menuitemradio"
                aria-checked={checked}
                className={`effort-menu-item ${checked ? "is-active" : ""}`.trim()}
                onClick={() => choose(option.value)}
              >
                <span className="effort-menu-text">
                  <span className="effort-menu-label">{option.label}</span>
                  <span className="effort-menu-desc">{option.description}</span>
                </span>
                {checked && <Check size={16} className="effort-menu-check" aria-hidden="true" />}
              </button>
            );
          })}
        </div>,
        document.body
      )
    : null;

  return (
    <>
      {menu}
      <button
        ref={triggerRef}
        type="button"
        className={`effort-trigger ${current.value !== "auto" ? "is-set" : ""}`.trim()}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        aria-label={`Mức suy luận: ${current.label}`}
        title="Mức suy luận"
        onClick={toggleMenu}
        onKeyDown={(event) => {
          if ((event.key === "ArrowUp" || event.key === "ArrowDown") && !open) {
            event.preventDefault();
            toggleMenu();
          }
        }}
      >
        <Brain size={16} aria-hidden="true" />
        <span className="effort-trigger-label">{current.label}</span>
        <ChevronDown size={14} className="effort-trigger-caret" aria-hidden="true" />
      </button>
    </>
  );
}

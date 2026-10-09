import React, { useCallback, useEffect, useRef } from "react";

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

/**
 * Hộp thoại có thể dùng bằng bàn phím.
 *
 * Ba điều kiện bắt buộc mà các modal cũ đều thiếu:
 *   - Đóng được bằng phím Esc.
 *   - Focus bị giữ bên trong (Tab không thoát ra nền phía sau).
 *   - Trả focus về đúng phần tử đã mở modal khi đóng.
 */
export default function Modal({
  open,
  onClose,
  title,
  description,
  icon,
  tone = "default",
  children,
  actions,
  labelledBy,
  closeOnBackdrop = true,
}) {
  const dialogRef = useRef(null);
  const previouslyFocused = useRef(null);
  const titleId = useRef(`modal-title-${Math.random().toString(36).slice(2, 9)}`).current;

  const handleClose = useCallback(() => {
    onClose?.();
  }, [onClose]);

  // Ghi nhớ phần tử đang focus trước khi mở, trả lại khi đóng.
  useEffect(() => {
    if (!open) return undefined;
    previouslyFocused.current = document.activeElement;

    const node = dialogRef.current;
    const first = node?.querySelector(FOCUSABLE);
    (first ?? node)?.focus();

    return () => {
      const target = previouslyFocused.current;
      if (target && typeof target.focus === "function" && document.contains(target)) {
        target.focus();
      }
    };
  }, [open]);

  // Esc để đóng, Tab để xoay vòng trong modal.
  useEffect(() => {
    if (!open) return undefined;

    function onKeyDown(event) {
      if (event.key === "Escape") {
        event.stopPropagation();
        handleClose();
        return;
      }
      if (event.key !== "Tab") return;

      const node = dialogRef.current;
      if (!node) return;
      const items = Array.from(node.querySelectorAll(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null || el === document.activeElement
      );
      if (items.length === 0) {
        event.preventDefault();
        node.focus();
        return;
      }

      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown, true);
    return () => document.removeEventListener("keydown", onKeyDown, true);
  }, [open, handleClose]);

  // Khoá cuộn nền để modal không trôi theo trang phía sau.
  useEffect(() => {
    if (!open) return undefined;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (closeOnBackdrop && event.target === event.currentTarget) handleClose();
      }}
    >
      <div
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy ?? titleId}
        tabIndex={-1}
      >
        {icon && (
          <div className={`modal-icon ${tone === "danger" ? "is-danger" : ""}`}>{icon}</div>
        )}
        {title && <h3 id={titleId}>{title}</h3>}
        {description && <p>{description}</p>}
        {children}
        {actions && <div className="modal-actions">{actions}</div>}
      </div>
    </div>
  );
}

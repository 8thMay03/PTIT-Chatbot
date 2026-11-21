import React, { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

/**
 * Hộp thoại ở giữa màn hình cho form thêm/sửa mô hình: header, thân tự cuộn, footer.
 *
 * Render qua portal vào `document.body`: vùng nội dung Cài đặt có `overflow: hidden`
 * và hiệu ứng vào trang nên `position: fixed` bên trong dễ bị cắt.
 * `onDismiss` thiếu (form đang có thay đổi hoặc đang lưu) thì Esc/scrim không đóng,
 * chỉ nút Huỷ trong footer đóng được, để không mất API key đang nhập dở.
 */
export default function ProfileDialog({ id, title, description, hidden = false, onDismiss, onClose, footer, children }) {
  const panelRef = useRef(null);
  const previousFocusRef = useRef(null);
  const dismissRef = useRef(onDismiss);
  dismissRef.current = onDismiss;

  // Ghi nhớ nút đã mở hộp thoại để trả focus khi đóng.
  useEffect(() => {
    previousFocusRef.current = document.activeElement;
    // Khoá cuộn nền như Modal để trang phía sau không trôi theo.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
      const target = previousFocusRef.current;
      if (target && document.contains(target)) target.focus?.({ preventScroll: true });
    };
  }, []);

  useEffect(() => {
    if (hidden) return undefined;
    const node = panelRef.current;
    if (node && !node.contains(document.activeElement)) {
      (node.querySelector(FOCUSABLE) ?? node).focus?.({ preventScroll: true });
    }

    function onKeyDown(event) {
      if (event.key === "Escape") {
        // Hộp thoại khác (Modal) đang mở phía trên thì để nó xử lý Esc.
        if (document.querySelector(".modal-backdrop")) return;
        event.stopPropagation();
        dismissRef.current?.();
        return;
      }
      if (event.key !== "Tab" || !node) return;
      const items = Array.from(node.querySelectorAll(FOCUSABLE)).filter(
        (item) => item.offsetParent !== null || item === document.activeElement
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
  }, [hidden]);

  return createPortal(
    <>
      <div
        className="mdl-dialog-scrim"
        hidden={hidden}
        aria-hidden="true"
        onClick={() => dismissRef.current?.()}
      />
      <aside
        ref={panelRef}
        className="mdl-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${id}-title`}
        hidden={hidden}
        tabIndex={-1}
      >
        <header className="mdl-dialog-head">
          <div className="mdl-dialog-heading">
            <h3 id={`${id}-title`}>{title}</h3>
            {description && <p>{description}</p>}
          </div>
          <button type="button" className="mdl-dialog-close" onClick={onClose} aria-label="Đóng">
            <X size={16} />
          </button>
        </header>
        <div className="mdl-dialog-body">{children}</div>
        {footer && <footer className="mdl-dialog-foot">{footer}</footer>}
      </aside>
    </>,
    document.body
  );
}

import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from "lucide-react";

const ToastContext = createContext(null);

const ICONS = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const DEFAULT_DURATION = { success: 4000, info: 4000, warning: 6000, error: 8000 };

/**
 * Hệ thống thông báo duy nhất của ứng dụng.
 *
 * Trước đây có ba cơ chế song song (toast riêng của ConfigView, banner trong
 * DatasetView, và window.confirm/alert), khiến cùng một loại sự kiện lại hiển
 * thị khác nhau tuỳ màn hình.
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef(new Map());

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((t) => t.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const push = useCallback(
    (message, type = "success", options = {}) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setToasts((current) => [...current, { id, message, type }]);

      const duration = options.duration ?? DEFAULT_DURATION[type] ?? 4000;
      if (duration > 0) {
        timers.current.set(
          id,
          setTimeout(() => dismiss(id), duration)
        );
      }
      return id;
    },
    [dismiss]
  );

  const api = useMemo(
    () => ({
      toast: push,
      success: (message, options) => push(message, "success", options),
      error: (message, options) => push(message, "error", options),
      warning: (message, options) => push(message, "warning", options),
      info: (message, options) => push(message, "info", options),
      dismiss,
    }),
    [push, dismiss]
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      {/* Lỗi phải được đọc ngay (assertive); thông báo thường thì chờ lượt (polite). */}
      <div className="toast-viewport" role="region" aria-label="Thông báo hệ thống">
        {toasts.map((item) => {
          const Icon = ICONS[item.type] ?? Info;
          return (
            <div
              key={item.id}
              className={`toast is-${item.type}`}
              role={item.type === "error" ? "alert" : "status"}
              aria-live={item.type === "error" ? "assertive" : "polite"}
            >
              <span className="toast-icon">
                <Icon size={17} />
              </span>
              <span className="toast-body">{item.message}</span>
              <button
                type="button"
                className="toast-close"
                onClick={() => dismiss(item.id)}
                aria-label="Đóng thông báo"
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast phải được dùng bên trong <ToastProvider>.");
  }
  return context;
}

import React from "react";
import { AlertCircle } from "lucide-react";

/**
 * Vùng thông báo lỗi chung của form. Luôn render vùng `aria-live` (kể cả khi rỗng)
 * để trình đọc màn hình đọc lỗi mới ngay khi xuất hiện.
 */
export default function FormAlert({ id, message }) {
  return (
    <div className="auth-alert-region" id={id} aria-live="assertive" aria-atomic="true">
      {message && (
        <div className="auth-alert is-danger">
          <AlertCircle size={16} aria-hidden="true" />
          <span>{message}</span>
        </div>
      )}
    </div>
  );
}

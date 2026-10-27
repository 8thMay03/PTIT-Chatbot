import React, { useState } from "react";
import { Loader2, LogIn, LogOut, X } from "lucide-react";
import { errorMessage } from "../api";
import { useAuthSession, useLogout, userInitial } from "../auth/session";
import { CHAT_PATH, authPageHref } from "../lib/appRoute";
import { useToast } from "./Toast";

export const GUEST_HINT_STORAGE_KEY = "ptit_chatbot_guest_hint_dismissed";

function readHintDismissed() {
  try {
    return localStorage.getItem(GUEST_HINT_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

/**
 * Khối tài khoản trên header chat: tên người dùng + Đăng xuất, hoặc nút Đăng nhập
 * cho khách. `onLoggedOut` để app chat đưa màn về hội thoại mới.
 */
export default function UserMenu({ onLoggedOut }) {
  const session = useAuthSession();
  const logout = useLogout();
  const toast = useToast();
  const [pending, setPending] = useState(false);

  if (session.isLoading) return null;

  if (!session.isAuthenticated) {
    return (
      <a className="user-login-btn" href={authPageHref("login", CHAT_PATH)}>
        <LogIn size={16} aria-hidden="true" />
        <span>Đăng nhập</span>
      </a>
    );
  }

  async function handleLogout() {
    if (pending) return;
    setPending(true);
    try {
      await logout();
      onLoggedOut?.();
    } catch (error) {
      toast.error(errorMessage(error, "Không đăng xuất được."));
    } finally {
      setPending(false);
    }
  }

  const { user } = session;
  return (
    <div className="user-menu">
      <span className="user-chip" title={user.email}>
        <span className="user-avatar" aria-hidden="true">
          {userInitial(user)}
        </span>
        <span className="user-name">{user.full_name}</span>
      </span>
      <button
        type="button"
        className="icon-btn"
        onClick={handleLogout}
        disabled={pending}
        aria-label={`Đăng xuất (${user.full_name})`}
        title="Đăng xuất"
      >
        {pending ? <Loader2 size={17} className="spin" /> : <LogOut size={17} />}
      </button>
    </div>
  );
}

/** Dòng nhắc nhẹ trong thanh bên cho khách; đóng được và nhớ bằng localStorage. */
export function GuestHint() {
  const session = useAuthSession();
  const [dismissed, setDismissed] = useState(readHintDismissed);

  if (session.isLoading || session.isAuthenticated || dismissed) return null;

  function dismiss() {
    setDismissed(true);
    try {
      localStorage.setItem(GUEST_HINT_STORAGE_KEY, "1");
    } catch {
      // Không lưu được thì chỉ ẩn trong phiên hiện tại.
    }
  }

  return (
    <div className="guest-hint">
      <p>
        <a href={authPageHref("login", CHAT_PATH)}>Đăng nhập</a> để lưu lịch sử trên mọi thiết bị.
      </p>
      <button type="button" className="guest-hint-close" onClick={dismiss} aria-label="Ẩn lời nhắc đăng nhập">
        <X size={14} aria-hidden="true" />
      </button>
    </div>
  );
}

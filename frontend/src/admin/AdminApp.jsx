import React, { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, RefreshCw, ShieldCheck } from "lucide-react";
import { adminApi, describeError, onUnauthorized, queryKeys } from "../api";
import Modal from "../components/Modal";
import { ToastProvider } from "../components/Toast";
import { authPageHref, navigateTo } from "../lib/appRoute";
import { AdminLoginForm } from "./AdminLogin";
import AdminShell from "./AdminShell";
import "../styles/admin.css";

const noop = () => {};

/**
 * App quản trị tại `/admin` (lazy-load từ main.jsx).
 *
 * - Chưa có phiên → chuyển sang trang `/login` chung (`?next=` giữ đúng màn đang mở).
 * - Backend chưa cấu hình ADMIN_EMAIL/ADMIN_PASSWORD → thẻ cảnh báo tại chỗ.
 * - Đã đăng nhập → shell Dataset/Settings.
 * - Phiên hết hạn giữa chừng (request admin trả 401) → lớp phủ đăng nhập, KHÔNG
 *   unmount shell để giữ bản nháp; đăng nhập lại thì refetch các query lỗi.
 */
export default function AdminApp() {
  const queryClient = useQueryClient();
  const sessionQuery = useQuery({
    queryKey: queryKeys.adminSession,
    queryFn: ({ signal }) => adminApi.session({ signal }),
    staleTime: 60_000,
  });
  // Đã vào shell trong lần tải trang này: từ đây mất phiên chỉ hiện lớp phủ.
  const [shellUnlocked, setShellUnlocked] = useState(false);
  const [expired, setExpired] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const session = sessionQuery.data;
  const authenticated = session?.authenticated === true;
  const configured = session?.configured !== false;

  useEffect(() => {
    if (authenticated) setShellUnlocked(true);
  }, [authenticated]);

  useEffect(
    () =>
      onUnauthorized(({ path }) => {
        // Sai mật khẩu ở form đăng nhập cũng là 401 nhưng không phải hết phiên.
        if (path.startsWith("admin/login")) return;
        setExpired(true);
      }),
    []
  );

  const handleLoggedIn = useCallback(
    (result) => {
      queryClient.setQueryData(queryKeys.adminSession, {
        authenticated: true,
        expires_at: result?.expires_at ?? null,
        configured: true,
      });
      setShellUnlocked(true);
      setExpired(false);
      // Request hỏng vì hết phiên được chạy lại; form đang sửa vẫn giữ nguyên.
      queryClient.refetchQueries({
        predicate: (query) =>
          query.state.status === "error" && query.queryKey[0] !== queryKeys.admin[0],
      });
    },
    [queryClient]
  );

  const handleLogout = useCallback(async () => {
    setLoggingOut(true);
    try {
      await adminApi.logout();
    } catch {
      // Logout chỉ xoá cookie; lỗi mạng vẫn đưa người dùng về form đăng nhập.
    } finally {
      // Không để dữ liệu quản trị (tài liệu, cấu hình) nằm lại trong cache.
      queryClient.clear();
      queryClient.setQueryData(queryKeys.adminSession, {
        authenticated: false,
        expires_at: null,
        configured,
      });
      setShellUnlocked(false);
      setExpired(false);
      setLoggingOut(false);
    }
  }, [queryClient, configured]);

  const showShell = shellUnlocked || authenticated;
  const redirectToLogin =
    !showShell && sessionQuery.isSuccess && !authenticated && configured;

  useEffect(() => {
    if (!redirectToLogin) return;
    const { pathname, hash } = window.location;
    navigateTo(authPageHref("login", `${pathname}${hash}`));
  }, [redirectToLogin]);

  if (!showShell) {
    if (sessionQuery.isPending) {
      return (
        <div className="app-loading" role="status">
          Đang kiểm tra phiên quản trị…
        </div>
      );
    }
    if (sessionQuery.isError) {
      const described = describeError(sessionQuery.error);
      return (
        <main className="admin-login-page">
          <section className="admin-login-card" role="alert">
            <div className="admin-login-alert is-danger">
              <AlertCircle size={16} aria-hidden="true" />
              <span>
                <strong>{described.title}.</strong> {described.detail}
              </span>
            </div>
            <button type="button" className="ghost-btn" onClick={() => sessionQuery.refetch()}>
              <RefreshCw size={15} aria-hidden="true" />
              Thử lại
            </button>
          </section>
        </main>
      );
    }
    if (!configured) return <AdminNotConfigured />;
    return (
      <div className="app-loading" role="status">
        Đang chuyển tới trang đăng nhập…
      </div>
    );
  }

  const showOverlay = expired || session?.authenticated === false;

  return (
    <ToastProvider>
      <AdminShell onLogout={handleLogout} loggingOut={loggingOut} inert={showOverlay} />
      <Modal
        open={showOverlay}
        onClose={noop}
        closeOnBackdrop={false}
        title="Phiên đăng nhập đã hết hạn"
        description="Đăng nhập lại để tiếp tục. Nội dung đang sửa vẫn được giữ nguyên."
      >
        <AdminLoginForm onSuccess={handleLoggedIn} />
      </Modal>
    </ToastProvider>
  );
}

/** Backend chưa bật quản trị: báo cách cấu hình thay vì chuyển sang /login. */
function AdminNotConfigured() {
  return (
    <main className="admin-login-page">
      <section className="admin-login-card" aria-labelledby="admin-config-title">
        <div className="admin-login-heading">
          <span className="brand-mark" aria-hidden="true">
            <ShieldCheck size={19} />
          </span>
          <div>
            <h1 id="admin-config-title">Quản trị PTIT Chatbot</h1>
            <p>Trang quản trị chưa được bật.</p>
          </div>
        </div>
        <div className="admin-login-alert is-warning" role="status">
          <AlertCircle size={16} aria-hidden="true" />
          <span>
            Backend chưa cấu hình <code>ADMIN_EMAIL</code> và <code>ADMIN_PASSWORD</code>. Đặt
            hai biến môi trường này rồi khởi động lại backend, sau đó đăng nhập tại trang đăng
            nhập chung bằng email quản trị.
          </span>
        </div>
        <a className="admin-login-back" href="/chat">
          ← Về trang chat
        </a>
      </section>
    </main>
  );
}

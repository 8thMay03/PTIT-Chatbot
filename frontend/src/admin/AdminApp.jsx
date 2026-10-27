import React, { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, RefreshCw } from "lucide-react";
import { adminApi, describeError, onUnauthorized, queryKeys } from "../api";
import Modal from "../components/Modal";
import { ToastProvider } from "../components/Toast";
import AdminLogin, { AdminLoginForm } from "./AdminLogin";
import AdminShell from "./AdminShell";
import "../styles/admin.css";

const noop = () => {};

/**
 * App quản trị tại `/admin` (lazy-load từ main.jsx).
 *
 * - Chưa có phiên → màn đăng nhập.
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
    return <AdminLogin configured={configured} onSuccess={handleLoggedIn} />;
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
        <AdminLoginForm configured={configured} onSuccess={handleLoggedIn} />
      </Modal>
    </ToastProvider>
  );
}

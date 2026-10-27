import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi, queryKeys } from "../api";

const GUEST_SESSION = { authenticated: false, user: null, registration_enabled: true };

/**
 * Trạng thái phiên người dùng từ `GET /auth/me` (query key `["auth", "me"]`).
 *
 * Lỗi mạng/máy chủ được coi như khách: trang landing và chat vẫn dùng được, chỉ
 * mất phần hiển thị tài khoản.
 */
export function useAuthSession() {
  const query = useQuery({
    queryKey: queryKeys.authMe,
    queryFn: ({ signal }) => authApi.me({ signal }),
    staleTime: 60_000,
  });
  const data = query.data ?? GUEST_SESSION;
  return {
    isLoading: query.isPending,
    isAuthenticated: Boolean(data.authenticated && data.user),
    user: data.authenticated ? data.user : null,
    registrationEnabled: data.registration_enabled !== false,
  };
}

/**
 * Ghi phiên vừa đăng nhập/đăng ký vào cache và bỏ cache hội thoại cũ (hội thoại ẩn
 * danh vừa được chuyển sang tài khoản nên danh sách đổi).
 */
export function useApplySignedIn() {
  const queryClient = useQueryClient();
  return useCallback(
    (session) => {
      queryClient.setQueryData(queryKeys.authMe, session);
      queryClient.invalidateQueries({ queryKey: queryKeys.auth });
      queryClient.removeQueries({ queryKey: queryKeys.conversations });
    },
    [queryClient]
  );
}

/**
 * Đăng xuất: backend xoá cookie tài khoản và cấp phiên ẩn danh mới; frontend xoá
 * cache hội thoại để không còn hiện lịch sử của tài khoản.
 */
export function useLogout() {
  const queryClient = useQueryClient();
  return useCallback(async () => {
    const session = await authApi.logout();
    // resetQueries (không phải removeQueries): danh sách đang hiển thị phải tải lại
    // ngay theo phiên ẩn danh mới, không giữ dữ liệu cũ của tài khoản.
    queryClient.resetQueries({ queryKey: queryKeys.conversations });
    const previous = queryClient.getQueryData(queryKeys.authMe);
    queryClient.setQueryData(queryKeys.authMe, {
      ...GUEST_SESSION,
      ...session,
      registration_enabled: previous?.registration_enabled ?? true,
    });
    queryClient.invalidateQueries({ queryKey: queryKeys.auth });
  }, [queryClient]);
}

/** Chữ cái đầu của tên cuối (kiểu tên tiếng Việt) để làm avatar. */
export function userInitial(user) {
  const parts = String(user?.full_name || user?.email || "").trim().split(/\s+/);
  const last = parts[parts.length - 1] || "";
  return last.charAt(0).toUpperCase() || "?";
}

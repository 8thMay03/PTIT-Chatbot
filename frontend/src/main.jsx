import React, { Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./api";
import {
  legacyHashToAdmin,
  legacyRootHashToChat,
  navigateTo,
  resolveAppRoute,
} from "./lib/appRoute";
import { playPixelEnter } from "./lib/motion/pixelTransition";
import "./styles/index.css";

// Mỗi trang là một chunk riêng: landing và trang tài khoản không tải mã chat
// (ChatView, markdown-it, DOMPurify) hay mã quản trị; trang chat không tải mã
// quản trị (Dataset, Settings, màn tài liệu chỉ tải khi mở /admin).
const PAGES = {
  landing: {
    Component: lazy(() => import("./landing/LandingPage")),
    loading: "Đang tải…",
  },
  chat: { Component: lazy(() => import("./App")), loading: "Đang tải trang trò chuyện…" },
  login: { Component: lazy(() => import("./auth/LoginPage")), loading: "Đang tải…" },
  register: { Component: lazy(() => import("./auth/RegisterPage")), loading: "Đang tải…" },
  admin: {
    Component: lazy(() => import("./admin/AdminApp")),
    loading: "Đang tải trang quản trị…",
  },
};

function renderApp() {
  const { pathname, hash } = window.location;
  const route = resolveAppRoute(pathname);
  // Link cũ #documents, #config, #models, #settings/* trỏ sang trang quản trị;
  // /#chat và /#settings/appearance (app chat cũ ở "/") trỏ sang /chat.
  const redirect =
    (route === "admin" ? null : legacyHashToAdmin(hash)) ?? legacyRootHashToChat(pathname, hash);
  if (redirect) {
    navigateTo(redirect);
    return;
  }

  // Trang trước vừa chạy pixel transition: phủ lưới ngay trước khi vẽ rồi cho tan.
  playPixelEnter();

  const { Component, loading } = PAGES[route];
  createRoot(document.getElementById("root")).render(
    <QueryClientProvider client={queryClient}>
      <Suspense
        fallback={
          <div className="app-loading" role="status">
            {loading}
          </div>
        }
      >
        <Component />
      </Suspense>
    </QueryClientProvider>
  );
}

renderApp();

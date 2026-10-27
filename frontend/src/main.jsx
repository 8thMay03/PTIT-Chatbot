import React, { Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { queryClient } from "./api";
import { isAdminPath, legacyHashToAdmin, navigateTo } from "./lib/appRoute";
import "./styles/index.css";

// Chunk admin (Dataset, Settings, màn tài liệu) chỉ tải khi mở /admin, nên trang
// chat của sinh viên không phải tải mã quản trị.
const AdminApp = lazy(() => import("./admin/AdminApp"));

function renderApp() {
  const adminTarget = isAdminPath(window.location.pathname)
    ? null
    : legacyHashToAdmin(window.location.hash);
  if (adminTarget) {
    // Link cũ #documents, #config, #models, #settings/* trỏ sang trang quản trị.
    navigateTo(adminTarget);
    return;
  }

  const content = isAdminPath(window.location.pathname) ? (
    <Suspense
      fallback={
        <div className="app-loading" role="status">
          Đang tải trang quản trị…
        </div>
      }
    >
      <AdminApp />
    </Suspense>
  ) : (
    <App />
  );

  createRoot(document.getElementById("root")).render(
    <QueryClientProvider client={queryClient}>{content}</QueryClientProvider>
  );
}

renderApp();

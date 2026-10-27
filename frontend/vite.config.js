import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const FRONTEND_ROOT = path.dirname(fileURLToPath(import.meta.url));

function normalizeModuleId(id) {
  const clean = id.replace(/^\0/, "").split("?")[0];
  if (!path.isAbsolute(clean)) return clean.replaceAll("\\", "/");
  return path.relative(FRONTEND_ROOT, clean).replaceAll("\\", "/");
}

/**
 * Ghi `dist/bundle-report.json` (chỉ khi BUNDLE_REPORT=1) để
 * `scripts/check-bundle.mjs` kiểm module nào nằm trong JS tải ban đầu (FE-06).
 */
function bundleReport() {
  return {
    name: "ptit-bundle-report",
    apply: "build",
    generateBundle(_options, bundle) {
      if (process.env.BUNDLE_REPORT !== "1") return;
      const chunks = Object.values(bundle)
        .filter((output) => output.type === "chunk")
        .map((chunk) => ({
          fileName: chunk.fileName,
          isEntry: chunk.isEntry,
          isDynamicEntry: chunk.isDynamicEntry,
          imports: chunk.imports,
          dynamicImports: chunk.dynamicImports,
          moduleIds: Object.keys(chunk.modules).map(normalizeModuleId).sort(),
        }));
      this.emitFile({
        type: "asset",
        fileName: "bundle-report.json",
        source: JSON.stringify({ chunks }, null, 2),
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), bundleReport()],
  test: {
    environment: "jsdom",
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    watch: {
      usePolling: true,
      interval: 300,
    },
    proxy: {
      "/api": {
        target: process.env.VITE_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
        // Gửi X-Forwarded-For để backend (TRUSTED_PROXY_IPS) chặn dò theo IP thật.
        xfwd: true,
      },
    },
  },
});

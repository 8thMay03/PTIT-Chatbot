#!/usr/bin/env node
/**
 * Kiểm JS tải ban đầu ở trang chat không chứa mã quản trị (FE-06, AC-04).
 *
 * Mặc định build lại vào `dist/` với BUNDLE_REPORT=1 rồi đọc
 * `dist/bundle-report.json` (plugin trong vite.config.js). Truyền `--no-build`
 * để dùng bản build sẵn có, `--out-dir <dir>` để đổi thư mục.
 *
 * JS ban đầu = chunk entry (index.html) + mọi chunk nó import tĩnh, đệ quy.
 * Fail khi chunk ban đầu chứa module trong FORBIDDEN, khi chunk admin không còn
 * (kiểm tra mất tác dụng), hoặc tổng gzip >= BASELINE_GZIP_BYTES.
 */
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const FRONTEND_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// Đo tại dev 8cf5f91 (trước khi tách app): assets/index-*.js 156.79 kB gzip.
const BASELINE_GZIP_BYTES = 156_790;

// Module chỉ được nằm trong chunk admin (plan FE-06, "Hợp đồng dùng chung").
const FORBIDDEN = [
  /^src\/admin\//,
  /^src\/(DatasetView|DocumentView|SettingsView|ConfigView|ModelsView)\.jsx$/,
  /^src\/components\/(MarkdownEditorView|ParserSelectionModal|OriginalDocumentViewer|ParseProgress)\.jsx$/,
  /^src\/lib\/(useParseJobs|parseJobs)\.js$/,
  /(^|\/)node_modules\/docx-preview\//,
];

function parseArgs(argv) {
  const options = { build: true, outDir: path.join(FRONTEND_ROOT, "dist") };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--no-build") options.build = false;
    else if (arg === "--out-dir") options.outDir = path.resolve(argv[++index]);
    else throw new Error(`Tham số không hỗ trợ: ${arg}`);
  }
  return options;
}

async function runBuild(outDir) {
  process.env.BUNDLE_REPORT = "1";
  const { build } = await import("vite");
  await build({ root: FRONTEND_ROOT, logLevel: "warn", build: { outDir, emptyOutDir: true } });
}

function initialChunks(chunks) {
  const byFile = new Map(chunks.map((chunk) => [chunk.fileName, chunk]));
  const seen = new Set();
  const queue = chunks.filter((chunk) => chunk.isEntry).map((chunk) => chunk.fileName);
  while (queue.length > 0) {
    const fileName = queue.shift();
    if (seen.has(fileName)) continue;
    seen.add(fileName);
    for (const imported of byFile.get(fileName)?.imports ?? []) queue.push(imported);
  }
  return [...seen].map((fileName) => byFile.get(fileName)).filter(Boolean);
}

function formatKb(bytes) {
  return `${(bytes / 1000).toFixed(2)} kB`;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.build) await runBuild(options.outDir);

  const reportPath = path.join(options.outDir, "bundle-report.json");
  if (!existsSync(reportPath)) {
    throw new Error(
      `Không thấy ${reportPath}. Chạy lại không có --no-build, hoặc build với BUNDLE_REPORT=1.`
    );
  }
  const { chunks } = JSON.parse(readFileSync(reportPath, "utf8"));
  const initial = initialChunks(chunks);
  const failures = [];

  if (initial.length === 0) failures.push("Không tìm thấy chunk entry nào trong báo cáo.");

  const adminChunk = chunks.find((chunk) => chunk.moduleIds.includes("src/admin/AdminApp.jsx"));
  if (!adminChunk) {
    failures.push("Không tìm thấy src/admin/AdminApp.jsx trong chunk nào — kiểm tra đường dẫn module.");
  } else if (initial.includes(adminChunk)) {
    failures.push(`AdminApp nằm trong JS ban đầu (${adminChunk.fileName}) thay vì chunk lazy.`);
  }

  let totalGzip = 0;
  console.log("JS tải ban đầu ở trang chat:");
  for (const chunk of initial) {
    const code = readFileSync(path.join(options.outDir, chunk.fileName));
    const gzipBytes = gzipSync(code).length;
    totalGzip += gzipBytes;
    console.log(`  ${chunk.fileName}  ${formatKb(code.length)} │ gzip ${formatKb(gzipBytes)}`);

    for (const moduleId of chunk.moduleIds) {
      if (FORBIDDEN.some((pattern) => pattern.test(moduleId))) {
        failures.push(`${chunk.fileName} chứa module quản trị ${moduleId}`);
      }
    }
  }
  console.log(
    `Tổng gzip JS ban đầu: ${formatKb(totalGzip)} (mốc phải nhỏ hơn: ${formatKb(BASELINE_GZIP_BYTES)})`
  );
  if (totalGzip >= BASELINE_GZIP_BYTES) {
    failures.push(`Tổng gzip ${formatKb(totalGzip)} không nhỏ hơn mốc ${formatKb(BASELINE_GZIP_BYTES)}.`);
  }

  if (failures.length > 0) {
    console.error("\ncheck:bundle THẤT BẠI:");
    failures.forEach((failure) => console.error(`  - ${failure}`));
    process.exitCode = 1;
    return;
  }
  console.log("check:bundle đạt.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

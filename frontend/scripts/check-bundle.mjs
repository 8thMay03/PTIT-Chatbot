#!/usr/bin/env node
/**
 * Kiểm JS tải ban đầu của từng trang (FE-06 AC-04, landing-user-auth AC-06).
 *
 * Mặc định build lại vào `dist/` với BUNDLE_REPORT=1 rồi đọc
 * `dist/bundle-report.json` (plugin trong vite.config.js). Truyền `--no-build`
 * để dùng bản build sẵn có, `--out-dir <dir>` để đổi thư mục.
 *
 * Mỗi trang là một chunk lazy từ entry (main.jsx). JS ban đầu của trang = chunk
 * entry + chunk của trang + mọi chunk chúng import tĩnh, đệ quy (Vite preload
 * cùng lúc). Fail khi:
 *   - không tìm thấy chunk của một trang (kiểm tra mất tác dụng);
 *   - landing/login/register chứa module chat hoặc module quản trị;
 *   - trang chat chứa module quản trị, hoặc tổng gzip vượt mức FE-06;
 *   - chunk admin nằm trong JS ban đầu của trang khác.
 */
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const FRONTEND_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// JS ban đầu của trang chat đo tại dev 04e3120 (FE-06 đã merge, trước task
// landing-user-auth): assets/index-*.js 369.55 kB, gzip 128.41 kB.
const CHAT_BASELINE_GZIP_BYTES = 128_410;

// Module chỉ được nằm trong chunk admin (plan FE-06, "Hợp đồng dùng chung").
const ADMIN_MODULES = [
  /^src\/admin\//,
  /^src\/(DatasetView|DocumentView|SettingsView|ConfigView|ModelsView)\.jsx$/,
  /^src\/components\/(MarkdownEditorView|ParserSelectionModal|OriginalDocumentViewer|ParseProgress)\.jsx$/,
  /^src\/lib\/(useParseJobs|parseJobs)\.js$/,
  /(^|\/)node_modules\/docx-preview\//,
];

// Module chỉ thuộc chunk chat (plan landing-user-auth, "Hợp đồng dùng chung").
const CHAT_MODULES = [
  /^src\/(App|ChatView)\.jsx$/,
  /^src\/components\/(MarkdownView|ReasoningPanel|ConversationList)\.jsx$/,
  /(^|\/)node_modules\/(markdown-it|dompurify)\//,
];

const PAGES = [
  { name: "landing (/)", module: "src/landing/LandingPage.jsx", forbidden: [...CHAT_MODULES, ...ADMIN_MODULES] },
  { name: "login (/login)", module: "src/auth/LoginPage.jsx", forbidden: [...CHAT_MODULES, ...ADMIN_MODULES] },
  {
    name: "register (/register)",
    module: "src/auth/RegisterPage.jsx",
    forbidden: [...CHAT_MODULES, ...ADMIN_MODULES],
  },
  {
    name: "chat (/chat)",
    module: "src/App.jsx",
    forbidden: ADMIN_MODULES,
    maxGzipBytes: CHAT_BASELINE_GZIP_BYTES,
  },
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

/** Các chunk tải cùng lúc khi mở `roots`: chính chúng + import tĩnh, đệ quy. */
function staticClosure(byFile, roots) {
  const seen = new Set();
  const queue = [...roots];
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
  const byFile = new Map(chunks.map((chunk) => [chunk.fileName, chunk]));
  const entries = chunks.filter((chunk) => chunk.isEntry).map((chunk) => chunk.fileName);
  const failures = [];
  const gzipCache = new Map();

  function gzipSize(chunk) {
    if (!gzipCache.has(chunk.fileName)) {
      const code = readFileSync(path.join(options.outDir, chunk.fileName));
      gzipCache.set(chunk.fileName, { raw: code.length, gzip: gzipSync(code).length });
    }
    return gzipCache.get(chunk.fileName);
  }

  if (entries.length === 0) failures.push("Không tìm thấy chunk entry nào trong báo cáo.");

  const chunkOf = (moduleId) => chunks.find((chunk) => chunk.moduleIds.includes(moduleId));
  const adminChunk = chunkOf("src/admin/AdminApp.jsx");
  if (!adminChunk) {
    failures.push("Không tìm thấy src/admin/AdminApp.jsx trong chunk nào — kiểm tra đường dẫn module.");
  }

  for (const page of PAGES) {
    const pageChunk = chunkOf(page.module);
    if (!pageChunk) {
      failures.push(`Không tìm thấy ${page.module} trong chunk nào — kiểm tra đường dẫn module.`);
      continue;
    }
    if (entries.includes(pageChunk.fileName)) {
      failures.push(`${page.module} nằm trong chunk entry thay vì chunk lazy của trang.`);
    }
    const initial = staticClosure(byFile, [...entries, pageChunk.fileName]);
    if (adminChunk && initial.includes(adminChunk)) {
      failures.push(`${page.name}: AdminApp nằm trong JS ban đầu (${adminChunk.fileName}).`);
    }

    let totalGzip = 0;
    console.log(`JS tải ban đầu — ${page.name}:`);
    for (const chunk of initial) {
      const size = gzipSize(chunk);
      totalGzip += size.gzip;
      console.log(`  ${chunk.fileName}  ${formatKb(size.raw)} │ gzip ${formatKb(size.gzip)}`);
      for (const moduleId of chunk.moduleIds) {
        if (page.forbidden.some((pattern) => pattern.test(moduleId))) {
          failures.push(`${page.name}: ${chunk.fileName} chứa module không được phép ${moduleId}`);
        }
      }
    }
    const limit = page.maxGzipBytes ? ` (mốc FE-06, không vượt: ${formatKb(page.maxGzipBytes)})` : "";
    console.log(`  Tổng gzip: ${formatKb(totalGzip)}${limit}\n`);
    if (page.maxGzipBytes && totalGzip > page.maxGzipBytes) {
      failures.push(
        `${page.name}: tổng gzip ${formatKb(totalGzip)} vượt mốc ${formatKb(page.maxGzipBytes)}.`
      );
    }
  }

  if (failures.length > 0) {
    console.error("check:bundle THẤT BẠI:");
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

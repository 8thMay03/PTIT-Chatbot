/**
 * Kiểm cấu hình nginx production (FE-14) không cần docker:
 *   - mọi <script> inline trong index.html có hash trong `script-src` của CSP, và CSP
 *     không giữ hash thừa (script đã sửa mà quên xoá hash cũ);
 *   - `script-src` không mở 'unsafe-inline'/'unsafe-eval';
 *   - mọi location có `add_header` trong nginx.conf include header bảo mật (nginx
 *     không kế thừa add_header cấp server vào location có add_header riêng).
 */
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const FRONTEND_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => readFileSync(path.join(FRONTEND_ROOT, relativePath), "utf8");

const SECURITY_INCLUDE = "include /etc/nginx/snippets/security-headers.conf;";
const PAGE_INCLUDE = "include /etc/nginx/snippets/page-headers.conf;";

function inlineScripts(html) {
  return [...html.matchAll(/<script(\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
    .filter((match) => !/\ssrc\s*=/i.test(match[1] ?? ""))
    .map((match) => match[2]);
}

function sha256Source(content) {
  return `'sha256-${createHash("sha256").update(content, "utf8").digest("base64")}'`;
}

function pageCspDirectives() {
  const conf = read("nginx/page-headers.conf");
  const headers = [...conf.matchAll(/^\s*add_header\s+Content-Security-Policy\s+"([^"]*)"\s+always;/gm)];
  expect(headers, "page-headers.conf phải có đúng một Content-Security-Policy (always)").toHaveLength(1);
  return new Map(
    headers[0][1]
      .split(";")
      .map((directive) => directive.trim().split(/\s+/))
      .filter(([name]) => name)
      .map(([name, ...sources]) => [name, sources])
  );
}

/** Tách các block `location … { … }` cấp một trong server (conf không lồng location). */
function locationBlocks(conf) {
  const stripped = conf.replace(/#.*$/gm, "");
  const blocks = [];
  const pattern = /location\s+([^{]+)\{/g;
  let match;
  while ((match = pattern.exec(stripped))) {
    let depth = 1;
    let index = pattern.lastIndex;
    while (depth > 0 && index < stripped.length) {
      if (stripped[index] === "{") depth += 1;
      if (stripped[index] === "}") depth -= 1;
      index += 1;
    }
    blocks.push({ name: match[1].trim(), body: stripped.slice(pattern.lastIndex, index - 1) });
  }
  return blocks;
}

describe("CSP cho trang SPA", () => {
  const scripts = inlineScripts(read("index.html"));
  const scriptSrc = pageCspDirectives().get("script-src") ?? [];

  it("index.html có theme script inline, lưu ở dạng LF", () => {
    expect(scripts.length).toBeGreaterThan(0);
    for (const script of scripts) {
      // CRLF đổi hash; .gitattributes cố định LF — checkout lại file nếu test này fail.
      expect(script.includes("\r"), "frontend/index.html phải dùng LF (xem .gitattributes)").toBe(false);
    }
  });

  it("script-src chứa đúng hash của mọi script inline, không thừa", () => {
    const expected = scripts.map(sha256Source).sort();
    const actual = scriptSrc.filter((source) => source.startsWith("'sha256-")).sort();
    expect(actual).toEqual(expected);
  });

  it("script-src không cho script inline/eval tùy ý", () => {
    expect(scriptSrc).toContain("'self'");
    expect(scriptSrc).not.toContain("'unsafe-inline'");
    expect(scriptSrc).not.toContain("'unsafe-eval'");
  });

  it("chặn nhúng trang từ origin khác", () => {
    expect(pageCspDirectives().get("frame-ancestors")).toEqual(["'self'"]);
    expect(pageCspDirectives().get("object-src")).toEqual(["'none'"]);
  });
});

describe("nginx.conf", () => {
  const conf = read("nginx.conf");
  const blocks = locationBlocks(conf);

  it("tìm thấy các location", () => {
    expect(blocks.map((block) => block.name)).toEqual(
      expect.arrayContaining(["= /api/chat/stream", "/api/", "^~ /assets/", "= /index.html", "/"])
    );
  });

  it("mọi location có header bảo mật", () => {
    for (const block of blocks) {
      const includesHeaders = block.body.includes(SECURITY_INCLUDE) || block.body.includes(PAGE_INCLUDE);
      expect(includesHeaders, `location ${block.name} thiếu include header bảo mật`).toBe(true);
    }
  });

  it("CSP trang chỉ gắn cho phần SPA, không cho /api/", () => {
    for (const block of blocks) {
      const isApi = /\/api\b/.test(block.name);
      expect(block.body.includes(PAGE_INCLUDE), `location ${block.name}`).toBe(!isApi);
    }
  });

  it("stream không buffer, không nén", () => {
    const stream = blocks.find((block) => block.name === "= /api/chat/stream");
    expect(stream.body).toMatch(/proxy_buffering\s+off;/);
    expect(stream.body).toMatch(/gzip\s+off;/);
  });
});

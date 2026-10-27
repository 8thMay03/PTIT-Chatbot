import { afterEach, describe, expect, it, vi } from "vitest";
import { request } from "./client";
import { ApiError } from "./errors";

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => "application/json" },
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}

function textResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => "text/plain" },
    json: async () => ({}),
    text: async () => body,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("request", () => {
  it("chuẩn hoá lỗi mạng thành ApiError mã network", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch"))
    );

    const error = await request("documents").catch((err) => err);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.code).toBe("network");
    expect(error.detail).toContain("không gọi được API");
  });

  it("giữ detail của backend khi 4xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: "Tên tài liệu không hợp lệ." }, 422)
      )
    );

    const error = await request("documents", {
      method: "POST",
      body: { title: "" },
    }).catch((err) => err);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(422);
    expect(error.detail).toBe("Tên tài liệu không hợp lệ.");
  });

  it("giữ mã trạng thái và nội dung lỗi khi 5xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(textResponse("Internal Server Error", 503))
    );

    const error = await request("config").catch((err) => err);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(503);
    expect(error.detail).toBe("Internal Server Error");
  });

  it("báo ApiError timeout khi request vượt quá thời gian chờ", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url, options) =>
          new Promise((_resolve, reject) => {
            options.signal.addEventListener(
              "abort",
              () => reject(new DOMException("Aborted", "AbortError")),
              { once: true }
            );
          })
      )
    );

    const outcome = request("documents").then(
      () => null,
      (err) => err
    );
    await vi.advanceTimersByTimeAsync(30_001);
    const error = await outcome;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.code).toBe("timeout");
    expect(error.detail).toContain("30 giây");
  });

  it("ném AbortError gốc khi caller huỷ, để màn hình bỏ qua", async () => {
    const controller = new AbortController();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url, options) =>
          new Promise((_resolve, reject) => {
            options.signal.addEventListener(
              "abort",
              () => reject(new DOMException("Aborted", "AbortError")),
              { once: true }
            );
          })
      )
    );

    const outcome = request("documents", {
      signal: controller.signal,
      timeout: 0,
    }).then(
      () => null,
      (err) => err
    );
    controller.abort();
    const error = await outcome;

    expect(error).not.toBeInstanceOf(ApiError);
    expect(error.name).toBe("AbortError");
  });
});

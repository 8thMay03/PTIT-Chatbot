import { describe, expect, it } from "vitest";
import { ApiError, describeError, isUnauthorized } from "./errors";

describe("describeError", () => {
  it("giữ chi tiết backend khi 5xx để người dùng biết nguyên nhân", () => {
    const described = describeError(
      new ApiError({ status: 503, detail: "LLM chưa được cấu hình." })
    );

    expect(described.kind).toBe("server");
    expect(described.detail).toContain("LLM chưa được cấu hình.");
  });

  it("phân biệt timeout với lỗi mạng", () => {
    const timeout = describeError(
      new ApiError({ status: 0, code: "timeout", detail: "Quá 30 giây." })
    );
    const network = describeError(
      new ApiError({ status: 0, code: "network", detail: "Mất kết nối." })
    );

    expect(timeout.kind).toBe("timeout");
    expect(network.kind).toBe("network");
  });

  it("phân loại 401 thành unauthorized để app admin hiện lại form đăng nhập", () => {
    const described = describeError(
      new ApiError({ status: 401, detail: "Cần đăng nhập quản trị." })
    );

    expect(described.kind).toBe("unauthorized");
    expect(described.detail).toBe("Cần đăng nhập quản trị.");
  });

  it("phân loại 403 thành forbidden (dành cho phân quyền sau này)", () => {
    const described = describeError(new ApiError({ status: 403, detail: "" }));

    expect(described.kind).toBe("forbidden");
    expect(described.title).toBe("Không có quyền thực hiện");
  });

  it("429 ưu tiên detail của backend (ví dụ chặn dò mật khẩu)", () => {
    const described = describeError(
      new ApiError({ status: 429, detail: "Quá nhiều lần đăng nhập sai. Thử lại sau ít phút." })
    );

    expect(described.kind).toBe("rate_limit");
    expect(described.detail).toContain("Thử lại sau ít phút");
  });
});

describe("isUnauthorized", () => {
  it("đúng với ApiError 401, sai với các lỗi khác", () => {
    expect(isUnauthorized(new ApiError({ status: 401, detail: "x" }))).toBe(true);
    expect(isUnauthorized(new ApiError({ status: 403, detail: "x" }))).toBe(false);
    expect(isUnauthorized(new ApiError({ status: 0, code: "network" }))).toBe(false);
    expect(isUnauthorized(new TypeError("boom"))).toBe(false);
    expect(isUnauthorized(null)).toBe(false);
  });
});

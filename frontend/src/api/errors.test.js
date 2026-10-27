import { describe, expect, it } from "vitest";
import { ApiError, describeError } from "./errors";

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
});

import { describe, expect, it } from "vitest";
import { ApiError, describeError, fieldErrors, isUnauthorized, STUDENT_ERROR_CONTEXT } from "./errors";

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

describe("describeError với ngữ cảnh sinh viên", () => {
  const network = new ApiError({ status: 0, code: "network", detail: "Kiểm tra server FastAPI." });
  const timeout = new ApiError({ status: 0, code: "timeout", detail: "Quá 30 giây." });
  const raw = new Error("Backend stream parse failed");

  it("mặc định giữ detail do client tạo và message gốc", () => {
    expect(describeError(network).detail).toBe("Kiểm tra server FastAPI.");
    expect(describeError(timeout).detail).toBe("Quá 30 giây.");
    expect(describeError(raw).detail).toBe("Backend stream parse failed");
  });

  it("networkDetail/timeoutDetail thay detail của client; showRawMessage false ẩn message gốc", () => {
    expect(describeError(network, STUDENT_ERROR_CONTEXT).detail).toBe(STUDENT_ERROR_CONTEXT.networkDetail);
    expect(describeError(new TypeError("Failed to fetch"), STUDENT_ERROR_CONTEXT).detail).toBe(
      STUDENT_ERROR_CONTEXT.networkDetail
    );
    expect(describeError(timeout, STUDENT_ERROR_CONTEXT).detail).toBe(STUDENT_ERROR_CONTEXT.timeoutDetail);
    expect(describeError(raw, STUDENT_ERROR_CONTEXT).detail).toBe(STUDENT_ERROR_CONTEXT.fallbackDetail);
  });

  it("5xx vẫn nối detail của backend (giữ mã tham chiếu)", () => {
    const described = describeError(
      new ApiError({ status: 500, detail: "Hệ thống đang bận. (Mã: ab12)" }),
      STUDENT_ERROR_CONTEXT
    );
    expect(described.detail).toContain(STUDENT_ERROR_CONTEXT.serverDetail);
    expect(described.detail).toContain("(Mã: ab12)");
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

describe("fieldErrors", () => {
  it("đọc lỗi 422 mặc định FastAPI theo trường trong body", () => {
    const error = new ApiError({
      status: 422,
      detail: "email: Email không đúng định dạng.",
      payload: {
        detail: [
          { loc: ["body", "email"], msg: "Email không đúng định dạng.", type: "email_format" },
          { loc: ["body", "password"], msg: "Mật khẩu phải có ít nhất 8 ký tự." },
          { loc: ["body", "password"], msg: "Lỗi thứ hai bị bỏ qua." },
          { loc: ["query", "limit"], msg: "Không thuộc body." },
        ],
      },
    });

    expect(fieldErrors(error)).toEqual({
      email: "Email không đúng định dạng.",
      password: "Mật khẩu phải có ít nhất 8 ký tự.",
    });
  });

  it("trả rỗng với lỗi khác 422 hoặc không có chi tiết theo trường", () => {
    expect(fieldErrors(new ApiError({ status: 409, payload: { detail: "Email đã được đăng ký." } }))).toEqual({});
    expect(fieldErrors(new ApiError({ status: 422, payload: { detail: "Sai." } }))).toEqual({});
    expect(fieldErrors(new Error("x"))).toEqual({});
  });
});

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  GUEST,
  STUDENT,
  buttonByText,
  callsTo,
  createBackend,
  inputByLabel,
  renderPage,
  submit,
  typeInto,
  waitFor,
} from "./authTestUtils";

const navigateTo = vi.fn();
vi.mock("../lib/appRoute", async (importOriginal) => ({
  ...(await importOriginal()),
  navigateTo: (url) => navigateTo(url),
}));

const { default: LoginPage } = await import("./LoginPage");

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("LoginPage", () => {
  let page;

  beforeEach(() => {
    navigateTo.mockReset();
    window.history.replaceState(null, "", "/login");
  });

  afterEach(() => {
    page?.unmount();
    vi.unstubAllGlobals();
  });

  async function fillAndSubmit(email = " SV@stu.ptit.edu.vn ", password = "mat-khau-1") {
    typeInto(inputByLabel(page.container, "Email"), email);
    typeInto(inputByLabel(page.container, "Mật khẩu"), password);
    await submit(page.container.querySelector("form"));
  }

  it("kiểm tra phía client, gắn lỗi vào ô bằng aria-describedby và không gọi API", async () => {
    const backend = createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<LoginPage />);

    typeInto(inputByLabel(page.container, "Email"), "khong-phai-email");
    await submit(page.container.querySelector("form"));

    const email = inputByLabel(page.container, "Email");
    expect(email.getAttribute("aria-invalid")).toBe("true");
    const describedBy = email.getAttribute("aria-describedby");
    expect(document.getElementById(describedBy).textContent).toBe(
      "Email không đúng định dạng."
    );
    expect(page.container.textContent).toContain("Vui lòng nhập mật khẩu.");
    expect(document.activeElement).toBe(email);
    expect(callsTo(backend, "POST auth/login")).toHaveLength(0);
  });

  it("đăng nhập thành công chuyển tới /chat mặc định với email đã chuẩn hoá", async () => {
    const backend = createBackend({ "GET auth/me": GUEST, "POST auth/login": STUDENT });
    page = await renderPage(<LoginPage />);

    await fillAndSubmit();

    await waitFor(() => navigateTo.mock.calls.length > 0);
    expect(navigateTo).toHaveBeenCalledWith("/chat");
    const [, options] = callsTo(backend, "POST auth/login")[0];
    expect(JSON.parse(options.body)).toEqual({ email: "sv@stu.ptit.edu.vn", password: "mat-khau-1" });
  });

  it.each([
    ["?next=%2Fchat%23settings%2Fappearance", "/chat#settings/appearance"],
    ["?next=%2F%2Fevil.com", "/chat"],
    ["?next=https%3A%2F%2Fevil.com", "/chat"],
    ["?next=javascript%3Aalert(1)", "/chat"],
  ])("next %s → %s", async (search, target) => {
    window.history.replaceState(null, "", `/login${search}`);
    createBackend({ "GET auth/me": GUEST, "POST auth/login": STUDENT });
    page = await renderPage(<LoginPage />);

    await fillAndSubmit();

    await waitFor(() => navigateTo.mock.calls.length > 0);
    expect(navigateTo).toHaveBeenCalledWith(target);
  });

  it.each([
    [401, { detail: "Email hoặc mật khẩu không đúng." }, "Email hoặc mật khẩu không đúng."],
    [429, { detail: "Quá nhiều lần thử." }, "Bạn đã thử quá nhiều lần. Vui lòng đợi vài phút rồi thử lại."],
    [503, { detail: "Bảo trì" }, "Máy chủ gặp sự cố"],
  ])("lỗi %i hiện thông báo tiếng Việt cạnh form", async (status, body, expected) => {
    createBackend({ "GET auth/me": GUEST, "POST auth/login": [status, body] });
    page = await renderPage(<LoginPage />);

    await fillAndSubmit();

    const form = page.container.querySelector("form");
    const alertId = await waitFor(() => form.getAttribute("aria-describedby"));
    const region = document.getElementById(alertId);
    expect(region.getAttribute("aria-live")).toBe("assertive");
    expect(region.textContent).toContain(expected);
    expect(navigateTo).not.toHaveBeenCalled();
    // Giữ giá trị đã nhập, nút gửi mở lại.
    expect(inputByLabel(page.container, "Email").value).toBe("SV@stu.ptit.edu.vn");
    expect(buttonByText(page.container, "Đăng nhập").disabled).toBe(false);
  });

  it("khoá nút gửi khi đang gửi, không gửi trùng", async () => {
    let resolveLogin;
    const backend = createBackend({
      "GET auth/me": GUEST,
      "POST auth/login": () =>
        new Promise((resolve) => {
          resolveLogin = resolve;
        }),
    });
    page = await renderPage(<LoginPage />);

    await fillAndSubmit();
    const button = page.container.querySelector('button[type="submit"]');
    expect(button.disabled).toBe(true);
    expect(button.textContent).toContain("Đang đăng nhập…");
    await submit(page.container.querySelector("form"));
    expect(callsTo(backend, "POST auth/login")).toHaveLength(1);

    await act(async () => {
      resolveLogin({
        ok: true,
        status: 200,
        headers: { get: () => "application/json" },
        json: () => Promise.resolve(STUDENT),
      });
    });
    await waitFor(() => navigateTo.mock.calls.length > 0);
  });

  it("nút hiện/ẩn mật khẩu đổi kiểu ô nhập", async () => {
    createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<LoginPage />);
    const password = inputByLabel(page.container, "Mật khẩu");
    const reveal = page.container.querySelector('button[aria-label="Hiện mật khẩu"]');

    expect(password.type).toBe("password");
    expect(password.getAttribute("autocomplete")).toBe("current-password");
    await act(async () => reveal.click());
    expect(password.type).toBe("text");
    expect(reveal.getAttribute("aria-pressed")).toBe("true");
    expect(reveal.getAttribute("aria-label")).toBe("Ẩn mật khẩu");
  });

  it("người đã đăng nhập mở /login được chuyển sang /chat", async () => {
    createBackend({ "GET auth/me": STUDENT });
    page = await renderPage(<LoginPage />);

    await waitFor(() => navigateTo.mock.calls.length > 0);
    expect(navigateTo).toHaveBeenCalledWith("/chat");
  });

  it("liên kết sang đăng ký giữ next", async () => {
    window.history.replaceState(null, "", "/login?next=%2Fadmin");
    createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<LoginPage />);

    const link = [...page.container.querySelectorAll("a")].find((a) => a.textContent === "Đăng ký");
    expect(link.getAttribute("href")).toBe("/register?next=%2Fadmin");
  });
});

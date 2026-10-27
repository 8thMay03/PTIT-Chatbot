import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  GUEST,
  STUDENT,
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

const { default: RegisterPage } = await import("./RegisterPage");

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("RegisterPage", () => {
  let page;

  beforeEach(() => {
    navigateTo.mockReset();
    window.history.replaceState(null, "", "/register");
  });

  afterEach(() => {
    page?.unmount();
    vi.unstubAllGlobals();
  });

  function fill({
    fullName = "  Trần   Thị Bình ",
    email = "SV@stu.ptit.edu.vn",
    password = "mat-khau-1",
    confirmPassword = password,
  } = {}) {
    typeInto(inputByLabel(page.container, "Họ và tên"), fullName);
    typeInto(inputByLabel(page.container, "Email"), email);
    typeInto(inputByLabel(page.container, "Mật khẩu"), password);
    typeInto(inputByLabel(page.container, "Nhập lại mật khẩu"), confirmPassword);
  }

  function errorOf(label) {
    const input = inputByLabel(page.container, label);
    const ids = (input.getAttribute("aria-describedby") || "").split(" ").filter(Boolean);
    return ids
      .map((id) => document.getElementById(id))
      .find((node) => node?.classList.contains("auth-field-error"))?.textContent;
  }

  it("kiểm tra phía client trùng quy tắc backend", async () => {
    const backend = createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<RegisterPage />);

    fill({ fullName: "   ", email: "a@b", password: "1234567", confirmPassword: "khac" });
    await submit(page.container.querySelector("form"));

    expect(errorOf("Họ và tên")).toBe("Vui lòng nhập họ tên.");
    expect(errorOf("Email")).toBe("Email không đúng định dạng.");
    expect(errorOf("Mật khẩu")).toBe("Mật khẩu phải có ít nhất 8 ký tự.");
    expect(errorOf("Nhập lại mật khẩu")).toBe("Mật khẩu nhập lại không khớp.");
    expect(document.activeElement).toBe(inputByLabel(page.container, "Họ và tên"));
    expect(callsTo(backend, "POST auth/register")).toHaveLength(0);

    // Sửa ô thì lỗi của ô đó biến mất.
    typeInto(inputByLabel(page.container, "Họ và tên"), "An");
    expect(errorOf("Họ và tên")).toBeUndefined();
  });

  it("autocomplete đúng cho từng ô", async () => {
    createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<RegisterPage />);

    expect(inputByLabel(page.container, "Họ và tên").getAttribute("autocomplete")).toBe("name");
    expect(inputByLabel(page.container, "Email").getAttribute("autocomplete")).toBe("email");
    expect(inputByLabel(page.container, "Mật khẩu").getAttribute("autocomplete")).toBe("new-password");
    expect(inputByLabel(page.container, "Nhập lại mật khẩu").getAttribute("autocomplete")).toBe(
      "new-password"
    );
  });

  it("đăng ký thành công gửi dữ liệu chuẩn hoá và chuyển tới next", async () => {
    window.history.replaceState(null, "", "/register?next=%2Fchat%23settings%2Fappearance");
    const backend = createBackend({ "GET auth/me": GUEST, "POST auth/register": [201, STUDENT] });
    page = await renderPage(<RegisterPage />);

    fill();
    await submit(page.container.querySelector("form"));

    await waitFor(() => navigateTo.mock.calls.length > 0);
    expect(navigateTo).toHaveBeenCalledWith("/chat#settings/appearance");
    const [, options] = callsTo(backend, "POST auth/register")[0];
    expect(JSON.parse(options.body)).toEqual({
      full_name: "Trần Thị Bình",
      email: "sv@stu.ptit.edu.vn",
      password: "mat-khau-1",
    });
  });

  it("409 gắn lỗi vào ô email và hiện thông báo chung", async () => {
    createBackend({
      "GET auth/me": GUEST,
      "POST auth/register": [409, { detail: "Email đã được đăng ký." }],
    });
    page = await renderPage(<RegisterPage />);

    fill();
    await submit(page.container.querySelector("form"));

    await waitFor(() => errorOf("Email") === "Email đã được đăng ký.");
    expect(page.container.querySelector(".auth-alert-region").textContent).toContain(
      "Email này đã có tài khoản"
    );
    expect(document.activeElement).toBe(inputByLabel(page.container, "Email"));
  });

  it("422 từ server gắn lỗi theo trường (full_name → Họ và tên)", async () => {
    createBackend({
      "GET auth/me": GUEST,
      "POST auth/register": [
        422,
        {
          detail: [
            { loc: ["body", "email"], msg: "Chỉ chấp nhận email thuộc tên miền: stu.ptit.edu.vn." },
            { loc: ["body", "full_name"], msg: "Họ tên tối đa 100 ký tự." },
          ],
        },
      ],
    });
    page = await renderPage(<RegisterPage />);

    fill();
    await submit(page.container.querySelector("form"));

    await waitFor(() => errorOf("Email"));
    expect(errorOf("Email")).toBe("Chỉ chấp nhận email thuộc tên miền: stu.ptit.edu.vn.");
    expect(errorOf("Họ và tên")).toBe("Họ tên tối đa 100 ký tự.");
    expect(page.container.querySelector(".auth-alert-region").textContent).toContain(
      "kiểm tra lại các ô"
    );
  });

  it("429 hiện thông báo thử lại sau", async () => {
    createBackend({ "GET auth/me": GUEST, "POST auth/register": [429, { detail: "x" }] });
    page = await renderPage(<RegisterPage />);

    fill();
    await submit(page.container.querySelector("form"));

    await waitFor(() =>
      page.container.querySelector(".auth-alert-region").textContent.includes("thử quá nhiều lần")
    );
  });

  it("503 ẩn form và báo tạm dừng đăng ký", async () => {
    createBackend({
      "GET auth/me": GUEST,
      "POST auth/register": [503, { detail: "Hệ thống đang tạm dừng đăng ký tài khoản mới." }],
    });
    page = await renderPage(<RegisterPage />);

    fill();
    await submit(page.container.querySelector("form"));

    await waitFor(() => page.container.querySelector("form") === null);
    expect(page.container.textContent).toContain("tạm dừng đăng ký");
  });

  it("backend báo tắt đăng ký thì không hiện form", async () => {
    createBackend({ "GET auth/me": { ...GUEST, registration_enabled: false } });
    page = await renderPage(<RegisterPage />);

    await waitFor(() => page.container.querySelector("form") === null);
    expect(page.container.querySelector('[role="status"]').textContent).toContain("tạm dừng đăng ký");
  });

  it("người đã đăng nhập mở /register được chuyển sang /chat", async () => {
    createBackend({ "GET auth/me": STUDENT });
    page = await renderPage(<RegisterPage />);

    await waitFor(() => navigateTo.mock.calls.length > 0);
    expect(navigateTo).toHaveBeenCalledWith("/chat");
  });
});

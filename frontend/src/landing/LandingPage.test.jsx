import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LandingPage from "./LandingPage";
import { GUEST, STUDENT, createBackend, renderPage, waitFor } from "../auth/authTestUtils";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function linkByText(container, text) {
  return [...container.querySelectorAll("a")].filter((item) => item.textContent.trim() === text);
}

describe("LandingPage", () => {
  let page;

  beforeEach(() => {
    localStorage.clear();
    window.history.replaceState(null, "", "/");
  });

  afterEach(() => {
    page?.unmount();
    vi.unstubAllGlobals();
  });

  it("có landmark header/main/footer, đúng một h1 và các khối nội dung", async () => {
    createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<LandingPage />);
    const { container } = page;

    expect(container.querySelectorAll("header")).toHaveLength(1);
    expect(container.querySelectorAll("main")).toHaveLength(1);
    expect(container.querySelectorAll("footer")).toHaveLength(1);
    expect(container.querySelectorAll("h1")).toHaveLength(1);
    expect(container.querySelector("h1").textContent).toContain("trích dẫn nguồn");

    const headings = [...container.querySelectorAll("h2")].map((item) => item.textContent);
    expect(headings).toEqual(
      expect.arrayContaining(["Chatbot giúp được gì", "Cách hoạt động", "Lưu ý khi sử dụng"])
    );
    expect(container.querySelector("#tinh-nang li")).not.toBeNull();
    expect(container.textContent).toContain("đối chiếu văn bản gốc");
    expect(container.textContent).toContain("có thể trả lời sai");
    // Skip link trỏ đúng tới vùng main.
    expect(container.querySelector('a.skip-link').getAttribute("href")).toBe("#landing-main");
    expect(container.querySelector("main").id).toBe("landing-main");
  });

  it("khách thấy CTA Bắt đầu trò chuyện, Đăng nhập, Đăng ký đúng đường dẫn", async () => {
    createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<LandingPage />);
    const { container } = page;

    await waitFor(() => linkByText(container, "Bắt đầu trò chuyện").length > 0);
    expect(linkByText(container, "Bắt đầu trò chuyện")[0].getAttribute("href")).toBe("/chat");
    expect(linkByText(container, "Đăng nhập").map((a) => a.getAttribute("href"))).toContain("/login");
    expect(linkByText(container, "Đăng ký").map((a) => a.getAttribute("href"))).toContain("/register");
    expect(linkByText(container, "Vào trò chuyện")).toHaveLength(0);
  });

  it("đã đăng nhập: CTA đổi thành Vào trò chuyện và hiện tên người dùng", async () => {
    createBackend({ "GET auth/me": STUDENT });
    page = await renderPage(<LandingPage />);
    const { container } = page;

    await waitFor(() => linkByText(container, "Vào trò chuyện").length > 0);
    expect(linkByText(container, "Vào trò chuyện").every((a) => a.getAttribute("href") === "/chat")).toBe(
      true
    );
    expect(container.textContent).toContain("Nguyễn Văn An");
    expect(linkByText(container, "Bắt đầu trò chuyện")).toHaveLength(0);
    expect(linkByText(container, "Đăng nhập")).toHaveLength(0);
    expect(linkByText(container, "Đăng ký")).toHaveLength(0);
  });

  it("lỗi gọi /auth/me vẫn hiện trang như khách", async () => {
    createBackend({ "GET auth/me": [500, { detail: "Lỗi" }] });
    page = await renderPage(<LandingPage />);

    await waitFor(() => linkByText(page.container, "Bắt đầu trò chuyện").length > 0);
  });

  it("nút đổi giao diện đảo sáng/tối", async () => {
    createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<LandingPage />);
    const toggle = page.container.querySelector(".theme-toggle");

    const { act } = await import("react");
    await act(async () => toggle.click());
    const first = document.documentElement.getAttribute("data-theme");
    await act(async () => toggle.click());
    const second = document.documentElement.getAttribute("data-theme");

    expect(new Set([first, second])).toEqual(new Set(["light", "dark"]));
  });
});

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  GUEST,
  STUDENT,
  buttonByText,
  createBackend,
  renderPage,
  submit,
  waitFor,
} from "../auth/authTestUtils";

const goTo = vi.fn();
vi.mock("../lib/appRoute", async (importOriginal) => ({
  ...(await importOriginal()),
  goTo: (url) => goTo(url),
}));

const { default: LandingPage } = await import("./LandingPage");

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function linksByText(container, text) {
  return [...container.querySelectorAll("a")].filter((item) => item.textContent.trim() === text);
}

function typeInTextarea(textarea, value) {
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
  act(() => {
    setter.call(textarea, value);
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

describe("LandingPage", () => {
  let page;

  beforeEach(() => {
    localStorage.clear();
    goTo.mockReset();
    window.history.replaceState(null, "", "/");
  });

  afterEach(() => {
    page?.unmount();
    vi.unstubAllGlobals();
  });

  it("có landmark header/main/footer, đúng một h1 và đủ các khối theo thiết kế", async () => {
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
      expect.arrayContaining([
        "Hiểu câu hỏi tiếng ViệtChatbot giúp được gì",
        "Cách hoạt động",
        "Câu hỏithường gặp",
      ])
    );
    // Bento 5 thẻ, dải chủ đề, carousel, FAQ, dải kêu gọi.
    expect(container.querySelectorAll(".lp-bento > li")).toHaveLength(5);
    expect(container.querySelectorAll(".lp-topic-strip li").length).toBeGreaterThan(0);
    expect(container.querySelector('[aria-roledescription="carousel"]')).not.toBeNull();
    expect(container.querySelectorAll(".lp-faq-item")).toHaveLength(6);
    expect(container.querySelector(".lp-cta")).not.toBeNull();
    // Lưu ý giới hạn luôn hiển thị (không nằm trong accordion đang đóng).
    expect(container.querySelector("#luu-y").textContent).toContain("có thể trả lời sai");
    expect(container.querySelector("#luu-y").textContent).toContain("đối chiếu văn bản gốc");
    expect(container.querySelector("a.skip-link").getAttribute("href")).toBe("#landing-main");
    expect(container.querySelector("main").id).toBe("landing-main");
    // Phần minh hoạ/nền chữ là trang trí, ẩn với trình đọc màn hình.
    expect(container.querySelector(".lp-bgtext").getAttribute("aria-hidden")).toBe("true");
    expect(container.querySelector(".lp-float-cards").getAttribute("aria-hidden")).toBe("true");
  });

  it("gắn điểm neo chuyển động; phần trang trí động ẩn với trình đọc màn hình", async () => {
    createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<LandingPage />);
    const { container } = page;

    // jsdom không có matchMedia → chuyển động tắt, không phần tử nào bị ẩn chờ reveal.
    expect(container.querySelector(".landing-page").classList.contains("motion-ready")).toBe(false);
    expect(container.querySelector("h1").getAttribute("data-reveal")).toBe("words");
    expect(container.querySelectorAll(".lp-bento > li[data-scrub='enter'][data-tilt]")).toHaveLength(5);
    // Mọi link sang trang khác trong landing đi qua pixel transition; link neo thì không.
    const pageLinks = [...container.querySelectorAll('a[href^="/"]')].filter((a) => a.getAttribute("href") !== "/");
    expect(pageLinks.length).toBeGreaterThan(0);
    expect(pageLinks.every((a) => a.hasAttribute("data-transition"))).toBe(true);
    expect(container.querySelector('a[href="#tinh-nang"]').hasAttribute("data-transition")).toBe(false);
    // Bản sao marquee và vòng chủ đề chỉ để trang trí.
    expect(container.querySelector(".lp-topic-strip.is-clone").getAttribute("aria-hidden")).toBe("true");
    expect(container.querySelector(".lp-ring").getAttribute("aria-hidden")).toBe("true");
    expect(container.querySelectorAll('ul.lp-topic-strip[aria-label="Chủ đề chatbot hỗ trợ"]')).toHaveLength(1);
  });

  it("khách thấy CTA Bắt đầu trò chuyện, Đăng nhập, Đăng ký đúng đường dẫn", async () => {
    createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<LandingPage />);
    const { container } = page;

    await waitFor(() => linksByText(container, "Bắt đầu trò chuyện").length > 0);
    expect(linksByText(container, "Bắt đầu trò chuyện").every((a) => a.getAttribute("href") === "/chat")).toBe(
      true
    );
    expect(linksByText(container, "Đăng nhập").map((a) => a.getAttribute("href"))).toContain("/login");
    expect(linksByText(container, "Đăng ký").map((a) => a.getAttribute("href"))).toContain("/register");
    expect(linksByText(container, "Vào trò chuyện")).toHaveLength(0);
  });

  it("đã đăng nhập: CTA đổi thành Vào trò chuyện và hiện tên người dùng", async () => {
    createBackend({ "GET auth/me": STUDENT });
    page = await renderPage(<LandingPage />);
    const { container } = page;

    await waitFor(() => linksByText(container, "Vào trò chuyện").length > 0);
    expect(linksByText(container, "Vào trò chuyện").every((a) => a.getAttribute("href") === "/chat")).toBe(
      true
    );
    expect(container.textContent).toContain("Nguyễn Văn An");
    expect(linksByText(container, "Bắt đầu trò chuyện")).toHaveLength(0);
    expect(linksByText(container, "Đăng nhập")).toHaveLength(0);
    expect(linksByText(container, "Đăng ký")).toHaveLength(0);
  });

  it("lỗi gọi /auth/me vẫn hiện trang như khách", async () => {
    createBackend({ "GET auth/me": [500, { detail: "Lỗi" }] });
    page = await renderPage(<LandingPage />);

    await waitFor(() => linksByText(page.container, "Bắt đầu trò chuyện").length > 0);
  });

  it("khung soạn: chip điền câu gợi ý, gửi mở /chat?q=, gửi rỗng mở /chat", async () => {
    createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<LandingPage />);
    const form = page.container.querySelector("form.lp-composer");
    const textarea = form.querySelector("textarea");

    await submit(form);
    expect(goTo).toHaveBeenLastCalledWith("/chat");

    await act(async () => buttonByText(form, "Học phí").click());
    expect(textarea.value).toBe("Học phí của sinh viên được quy định như thế nào?");

    typeInTextarea(textarea, "  Điều kiện tốt nghiệp?  ");
    await submit(form);
    expect(goTo).toHaveBeenLastCalledWith(`/chat?q=${encodeURIComponent("Điều kiện tốt nghiệp?")}`);

    // Enter gửi, Shift+Enter xuống dòng.
    goTo.mockClear();
    await act(async () => {
      textarea.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", shiftKey: true, bubbles: true }));
    });
    expect(goTo).not.toHaveBeenCalled();
    await act(async () => {
      textarea.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    });
    expect(goTo).toHaveBeenCalledTimes(1);
  });

  it("carousel Cách hoạt động chuyển bước bằng nút trước/sau và ô chọn", async () => {
    createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<LandingPage />);
    const carousel = page.container.querySelector('[aria-roledescription="carousel"]');
    const slide = () => carousel.querySelector('[aria-roledescription="slide"]');
    const next = carousel.querySelector('button[aria-label="Bước tiếp theo"]');
    const prev = carousel.querySelector('button[aria-label="Bước trước"]');

    expect(slide().getAttribute("aria-label")).toBe("Bước 1 trên 4");
    expect(next.getAttribute("aria-controls")).toBe(slide().id);
    await act(async () => next.click());
    expect(slide().getAttribute("aria-label")).toBe("Bước 2 trên 4");
    expect(slide().textContent).toContain("Tìm trong tài liệu chính thức");
    await act(async () => prev.click());
    await act(async () => prev.click());
    expect(slide().getAttribute("aria-label")).toBe("Bước 4 trên 4");

    const thumb = carousel.querySelector('button[aria-label^="Bước 3:"]');
    await act(async () => thumb.click());
    expect(slide().getAttribute("aria-label")).toBe("Bước 3 trên 4");
    expect(thumb.getAttribute("aria-current")).toBe("step");
  });

  it("FAQ mở/đóng từng câu với aria-expanded và aria-controls", async () => {
    createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<LandingPage />);
    const buttons = [...page.container.querySelectorAll(".lp-faq-question button")];
    const panelOf = (button) => document.getElementById(button.getAttribute("aria-controls"));

    expect(buttons).toHaveLength(6);
    expect(buttons.every((button) => button.getAttribute("aria-expanded") === "false")).toBe(true);
    expect(panelOf(buttons[3]).hidden).toBe(true);

    await act(async () => buttons[3].click());
    expect(buttons[3].getAttribute("aria-expanded")).toBe("true");
    expect(panelOf(buttons[3]).hidden).toBe(false);
    expect(panelOf(buttons[3]).textContent).toContain("có thể trả lời sai");

    // Mở câu khác thì câu trước đóng; bấm lại thì đóng.
    await act(async () => buttons[0].click());
    expect(buttons[3].getAttribute("aria-expanded")).toBe("false");
    await act(async () => buttons[0].click());
    expect(buttons[0].getAttribute("aria-expanded")).toBe("false");
  });

  it("nút đổi giao diện đảo sáng/tối", async () => {
    createBackend({ "GET auth/me": GUEST });
    page = await renderPage(<LandingPage />);
    const toggle = page.container.querySelector(".theme-toggle");

    await act(async () => toggle.click());
    const first = document.documentElement.getAttribute("data-theme");
    await act(async () => toggle.click());
    const second = document.documentElement.getAttribute("data-theme");

    expect(new Set([first, second])).toEqual(new Set(["light", "dark"]));
  });
});

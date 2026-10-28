import React, { act, useRef } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const goTo = vi.fn();
vi.mock("../../lib/appRoute", async (importOriginal) => ({
  ...(await importOriginal()),
  goTo: (url) => goTo(url),
}));

const { default: SplitWords } = await import("./SplitWords");
const { shouldIntercept, transitionTo } = await import("./pixelTransition");
const { default: useLandingMotion } = await import("./useLandingMotion");

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

/** matchMedia giả: `reduce` = người dùng bật giảm chuyển động. */
function stubMatchMedia({ reduce = false, hover = true } = {}) {
  vi.stubGlobal("matchMedia", (query) => ({
    matches: query.includes("reduced-motion") ? reduce : query.includes("hover") ? hover : false,
    media: query,
    addEventListener() {},
    removeEventListener() {},
  }));
}

function render(element) {
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  act(() => root.render(element));
  return {
    container,
    unmount() {
      act(() => root.unmount());
      container.remove();
    },
  };
}

function MotionHost() {
  const ref = useRef(null);
  useLandingMotion(ref);
  return (
    <div className="landing-page" ref={ref}>
      <header className="lp-nav" />
      <h2 data-reveal="words">
        <SplitWords text="Câu hỏi thường gặp" />
      </h2>
      <p data-reveal="up">Nội dung</p>
      <a href="/chat" data-transition data-pulse>
        Vào trò chuyện
      </a>
    </div>
  );
}

let view;

beforeEach(() => {
  goTo.mockReset();
});

afterEach(() => {
  view?.unmount();
  view = null;
  // Lớp phủ là trạng thái cấp module: gỡ bằng đúng đường bfcache của mã thật.
  const pageshow = new Event("pageshow");
  pageshow.persisted = true;
  window.dispatchEvent(pageshow);
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("SplitWords", () => {
  it("tách từ nhưng giữ nguyên textContent và thứ tự --i", () => {
    view = render(
      <h1>
        <SplitWords text="Hỏi đáp  quy chế PTIT" start={2} />
      </h1>
    );
    const heading = view.container.querySelector("h1");
    expect(heading.textContent).toBe("Hỏi đáp quy chế PTIT");
    const words = [...heading.querySelectorAll(".lp-word")];
    expect(words).toHaveLength(5);
    expect(words.map((word) => word.style.getPropertyValue("--i"))).toEqual(["2", "3", "4", "5", "6"]);
  });
});

describe("useLandingMotion", () => {
  it("không có matchMedia (jsdom): không bật chuyển động, nội dung không bị ẩn", () => {
    view = render(<MotionHost />);
    const root = view.container.querySelector(".landing-page");
    expect(root.classList.contains("motion-ready")).toBe(false);
  });

  it("người dùng giảm chuyển động: không bật chuyển động", () => {
    stubMatchMedia({ reduce: true });
    view = render(<MotionHost />);
    expect(view.container.querySelector(".landing-page").classList.contains("motion-ready")).toBe(false);
  });

  it("bật chuyển động nhưng thiếu IntersectionObserver: mọi data-reveal hiện ngay", () => {
    stubMatchMedia();
    vi.stubGlobal("IntersectionObserver", undefined);
    view = render(<MotionHost />);
    const root = view.container.querySelector(".landing-page");
    expect(root.classList.contains("motion-ready")).toBe(true);
    const targets = [...root.querySelectorAll("[data-reveal]")];
    expect(targets.length).toBe(2);
    expect(targets.every((element) => element.classList.contains("is-revealed"))).toBe(true);
    expect(root.querySelector(".lp-nav").dataset.navState).toBe("top");
  });

  it("reveal khi phần tử vào khung nhìn và gỡ observer khi unmount", () => {
    stubMatchMedia();
    const observers = [];
    vi.stubGlobal(
      "IntersectionObserver",
      class {
        constructor(callback) {
          this.callback = callback;
          this.targets = [];
          this.disconnect = vi.fn();
          observers.push(this);
        }
        observe(target) {
          this.targets.push(target);
        }
        unobserve(target) {
          this.targets = this.targets.filter((item) => item !== target);
        }
      }
    );
    view = render(<MotionHost />);
    const [observer] = observers;
    const paragraph = view.container.querySelector("p[data-reveal]");
    expect(paragraph.classList.contains("is-revealed")).toBe(false);

    observer.callback([{ target: paragraph, isIntersecting: true }]);
    expect(paragraph.classList.contains("is-revealed")).toBe(true);
    expect(observer.targets).not.toContain(paragraph);

    const root = view.container.querySelector(".landing-page");
    view.unmount();
    view = null;
    expect(observer.disconnect).toHaveBeenCalled();
    expect(root.classList.contains("motion-ready")).toBe(false);
  });

  it("click link data-transition: chạy pixel transition rồi mới chuyển trang; Ctrl+click để mặc định", () => {
    stubMatchMedia();
    vi.useFakeTimers();
    view = render(<MotionHost />);
    const link = view.container.querySelector("a[data-transition]");
    // Ghi lại quyết định của hook rồi chặn điều hướng thật (jsdom không hỗ trợ).
    const prevented = [];
    const record = (event) => {
      prevented.push(event.defaultPrevented);
      event.preventDefault();
    };
    document.addEventListener("click", record);

    link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, ctrlKey: true }));
    expect(prevented).toEqual([false]);
    expect(document.querySelector(".lp-pixels")).toBeNull();

    link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, detail: 1 }));
    document.removeEventListener("click", record);
    expect(prevented).toEqual([false, true]);
    expect(document.querySelector(".lp-pixels")).not.toBeNull();
    expect(link.querySelector(".lp-pulse")).not.toBeNull();
    expect(goTo).not.toHaveBeenCalled();

    vi.advanceTimersByTime(700);
    expect(goTo).toHaveBeenCalledWith("/chat");
  });
});

describe("pixelTransition", () => {
  it("tắt chuyển động thì chuyển trang ngay, không tạo lớp phủ", () => {
    transitionTo("/login");
    expect(goTo).toHaveBeenCalledWith("/login");
    expect(document.querySelector(".lp-pixels")).toBeNull();
  });

  it("gỡ lớp phủ khi trang được khôi phục từ bfcache", () => {
    stubMatchMedia();
    vi.useFakeTimers();
    transitionTo("/chat");
    expect(document.querySelector(".lp-pixels")).not.toBeNull();
    // Gọi lại trong lúc đang chuyển thì không tạo thêm lớp phủ.
    transitionTo("/chat");
    expect(document.querySelectorAll(".lp-pixels")).toHaveLength(1);

    const pageshow = new Event("pageshow");
    pageshow.persisted = true;
    window.dispatchEvent(pageshow);
    expect(document.querySelector(".lp-pixels")).toBeNull();
  });

  it("chỉ chặn click chuột trái thường trên link cùng origin", () => {
    const anchor = document.createElement("a");
    anchor.href = "/chat";
    const event = (init = {}) => new MouseEvent("click", { button: 0, ...init });

    expect(shouldIntercept(event(), anchor)).toBe(true);
    for (const modifier of ["metaKey", "ctrlKey", "shiftKey", "altKey"]) {
      expect(shouldIntercept(event({ [modifier]: true }), anchor)).toBe(false);
    }
    expect(shouldIntercept(event({ button: 1 }), anchor)).toBe(false);

    anchor.target = "_blank";
    expect(shouldIntercept(event(), anchor)).toBe(false);
    anchor.removeAttribute("target");

    anchor.href = "https://example.com/chat";
    expect(shouldIntercept(event(), anchor)).toBe(false);
  });
});

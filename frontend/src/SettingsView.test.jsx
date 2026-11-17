import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SettingsView from "./SettingsView";
import { ToastProvider } from "./components/Toast";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function jsonResponse(payload, status = 200) {
  return Promise.resolve({
    ok: status < 400,
    status,
    headers: new Headers({ "content-type": "application/json" }),
    json: () => Promise.resolve(payload),
  });
}

function baseConfig() {
  return {
    llm: { provider: "openai", model: "gpt-4.1-mini", temperature: 0, timeout: 30, max_retries: 2 },
    retrieval: {
      top_k: 4,
      hybrid_vector_weight: 0.65,
      multi_query_enabled: true,
      multi_query_count: 3,
      multi_query_use_llm: false,
      query_rewrite_use_llm: false,
    },
    reranker: { enabled: true, provider: "heuristic", model: "cross-encoder/x", candidate_multiplier: 3 },
    guardrails: {
      scope_enabled: true,
      min_vector_score: 0.37,
      min_bm25_norm_score: 0.25,
      min_rerank_score: null,
      vector_threshold_source: "calibrated",
      calibrated_min_vector_score: 0.37,
      rerank_threshold_source: "not_applicable",
      calibrated_min_rerank_score: -1.65,
    },
    embedding: { provider: "openai", model: "text-embedding-3-small" },
    updated_at: new Date().toISOString(),
  };
}

function emptyRegistry() {
  return {
    profiles: [],
    active: { llm: null, embedding: null, reranker: null },
    embedding_runtime: { profile_id: null, restart_required: false, load_error: null },
    env_defaults: {},
    secret_encryption_enabled: true,
  };
}

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((url) => {
      const path = new URL(String(url), "http://test").pathname.replace(/^\/api\//, "");
      if (path === "config") return jsonResponse(baseConfig());
      if (path === "model-profiles") return jsonResponse(emptyRegistry());
      if (path === "datasets") return jsonResponse({ datasets: [] });
      return jsonResponse({ detail: path }, 500);
    })
  );
}

async function waitFor(check, timeout = 1500) {
  const started = Date.now();
  let lastError;
  while (Date.now() - started < timeout) {
    try {
      const value = check();
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });
  }
  throw lastError ?? new Error("Hết thời gian chờ trạng thái giao diện.");
}

async function click(element) {
  await act(async () => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

async function changeInput(input, value) {
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

describe("SettingsView — danh mục dọc và form theo pipeline", () => {
  let container;
  let root;
  let queryClient;

  beforeEach(() => {
    localStorage.clear();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  async function render(props = {}) {
    await act(async () => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <SettingsView theme="light" onThemeChange={() => {}} {...props} />
          </ToastProvider>
        </QueryClientProvider>
      );
    });
    await waitFor(() => container.querySelector("#cfg-topk"));
  }

  it("mặc định mở form Hệ thống trả lời với Lần lưu gần nhất ở header", async () => {
    stubFetch();
    await render();

    expect(container.querySelector("#settings-panel-answer").hidden).toBe(false);
    expect(container.querySelector("#settings-panel-models").hidden).toBe(true);
    expect(container.querySelector("#settings-panel-appearance").hidden).toBe(true);
    expect(container.querySelector(".settings-head-title-row h2").textContent).toBe(
      "Hệ thống trả lời"
    );
    const saved = container.querySelector(".settings-saved").textContent;
    expect(saved).toContain("Lần lưu gần nhất:");
    expect(saved).toContain("hôm nay");
  });

  it("chuyển mục trong nhóm trả lời đổi aria-current và gọi onSectionChange", async () => {
    stubFetch();
    const onSectionChange = vi.fn();
    await render({ section: "retrieval", onSectionChange });

    await click(container.querySelector('[data-settings-nav="gate"]'));

    expect(onSectionChange).toHaveBeenCalledWith("gate");
    expect(container.querySelector('[data-settings-nav="gate"]').getAttribute("aria-current")).toBe(
      "location"
    );
  });

  it("bấm Truy xuất khi đang ở #settings vẫn cuộn tới mục dù section quy về cùng anchor", async () => {
    stubFetch();
    const scrolled = [];
    const originalScroll = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = function scrollIntoView() {
      scrolled.push(this.id);
    };
    try {
      // Như AdminShell: onSectionChange đổi `section` của route rồi render lại.
      const onSectionChange = vi.fn((next) => render({ section: next, onSectionChange }));
      await render({ section: null, onSectionChange });
      const before = scrolled.filter((id) => id === "settings-section-retrieval").length;

      await click(container.querySelector('[data-settings-nav="retrieval"]'));
      await waitFor(
        () => scrolled.filter((id) => id === "settings-section-retrieval").length === before + 1
      );

      await click(container.querySelector('[data-settings-nav="retrieval"]'));
      await waitFor(
        () => scrolled.filter((id) => id === "settings-section-retrieval").length === before + 2
      );
      expect(onSectionChange).toHaveBeenCalledTimes(2);
    } finally {
      Element.prototype.scrollIntoView = originalScroll;
    }
  });

  it("mục có thay đổi chưa lưu hiện chấm", async () => {
    stubFetch();
    await render({ section: "retrieval" });

    expect(container.querySelector('[data-settings-nav="retrieval"] .settings-dirty-dot')).toBeNull();
    await changeInput(container.querySelector("#cfg-topk"), "6");
    await waitFor(() =>
      container.querySelector('[data-settings-nav="retrieval"] .settings-dirty-dot')
    );
  });

  it("mục Mô hình mở đúng panel loại mô hình, không trộn form trả lời", async () => {
    stubFetch();
    await render({ section: "models-embedding" });

    expect(container.querySelector("#settings-panel-models").hidden).toBe(false);
    expect(container.querySelector("#settings-panel-answer").hidden).toBe(true);
    expect(container.querySelector("#mdl-panel-embedding").hidden).toBe(false);
    expect(container.querySelector("#mdl-panel-llm").hidden).toBe(true);
    expect(container.querySelector(".settings-head-title-row h2").textContent).toBe("Mô hình");
  });

  it("mục Giao diện mở bộ chọn giao diện", async () => {
    stubFetch();
    await render({ section: "appearance" });

    expect(container.querySelector("#settings-panel-appearance").hidden).toBe(false);
    expect(container.querySelector('[aria-label="Chế độ giao diện"]')).not.toBeNull();
  });

  it("nút Thử với câu hỏi mở drawer trên khổ hẹp", async () => {
    stubFetch();
    await render({ section: "retrieval" });

    const trigger = container.querySelector(".settings-test-trigger");
    const panel = container.querySelector(".retrieval-test-panel");
    expect(panel.getAttribute("data-open")).toBe("false");

    await click(trigger);
    expect(panel.getAttribute("data-open")).toBe("true");
  });

  it("form không còn lưới hai cột cũ và theo thứ tự pipeline", async () => {
    stubFetch();
    await render({ section: "retrieval" });

    expect(container.querySelector(".config-two-col-grid")).toBeNull();
    const sections = [...container.querySelectorAll(".config-section")].map((node) => node.id);
    expect(sections).toEqual([
      "settings-section-retrieval",
      "settings-section-reranker",
      "settings-section-gate",
      "settings-section-generation",
    ]);
    expect(container.querySelector('button[aria-labelledby="cfg-rewrite-label"]')).not.toBeNull();
  });
});

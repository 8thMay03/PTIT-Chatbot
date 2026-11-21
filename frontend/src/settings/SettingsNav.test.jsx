import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SettingsIndex, SettingsTabs, settingsGroupOf } from "./SettingsNav";
import PipelineSteps from "./PipelineSteps";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("SettingsNav", () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  async function render(node) {
    await act(async () => {
      root.render(node);
    });
  }

  async function click(element, init = {}) {
    await act(async () => {
      element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, ...init }));
    });
  }

  it("ba tab nhóm trỏ tới mục đầu của nhóm, tab đang mở có aria-current", async () => {
    const onSelect = vi.fn();
    await render(<SettingsTabs group="models" onSelect={onSelect} />);

    const tabs = [...container.querySelectorAll("[data-settings-tab]")];
    expect(tabs.map((tab) => [tab.textContent.trim(), tab.getAttribute("href")])).toEqual([
      ["Hệ thống trả lời", "#settings/retrieval"],
      ["Mô hình", "#settings/models-llm"],
      ["Giao diện", "#settings/appearance"],
    ]);
    expect(tabs.map((tab) => tab.getAttribute("aria-current"))).toEqual([null, "page", null]);

    await click(tabs[2]);
    expect(onSelect).toHaveBeenCalledWith("appearance");
  });

  it("tab Hệ thống trả lời hiện chấm khi bản nháp có thay đổi", async () => {
    await render(<SettingsTabs group="personal" dirty onSelect={() => {}} />);

    expect(container.querySelector('[data-settings-tab="answer"] .settings-dirty-dot')).not.toBeNull();
    expect(container.querySelector('[data-settings-tab="models"] .settings-dirty-dot')).toBeNull();
  });

  it("Ctrl+click giữ hành vi mở tab mới của trình duyệt", async () => {
    const onSelect = vi.fn();
    await render(<SettingsTabs group="answer" onSelect={onSelect} />);

    await click(container.querySelector('[data-settings-tab="models"]'), { ctrlKey: true });
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("dải bước theo thứ tự pipeline, hiện giá trị và chấm chưa lưu", async () => {
    const onSelect = vi.fn();
    await render(
      <PipelineSteps
        activeKey="gate"
        summaries={{ retrieval: ["Top-K 4", "Vector 65%"], gate: ["BM25 ≥ 0.25"] }}
        dirtySections={["retrieval"]}
        onSelect={onSelect}
      />
    );

    const steps = [...container.querySelectorAll(".pipeline-step")];
    expect(steps.map((step) => step.getAttribute("href"))).toEqual([
      "#settings/retrieval",
      "#settings/reranker",
      "#settings/gate",
      "#settings/generation",
    ]);
    expect(steps[0].textContent).toContain("Bước 1");
    expect(steps[0].textContent).toContain("Top-K 4");
    expect(steps[0].querySelector(".settings-dirty-dot")).not.toBeNull();
    expect(steps[2].querySelector(".settings-dirty-dot")).toBeNull();
    expect(steps[2].getAttribute("aria-current")).toBe("step");
    expect(steps[0].getAttribute("aria-current")).toBeNull();

    await click(steps[3]);
    expect(onSelect).toHaveBeenCalledWith("generation");
  });

  it("danh sách mobile hiện giá trị đang dùng (nếu có) và gọi onSelect", async () => {
    const onSelect = vi.fn();
    await render(
      <SettingsIndex
        dirtySections={["reranker"]}
        summaries={{ retrieval: ["Top-K 4", "Vector 65%"] }}
        onSelect={onSelect}
      />
    );

    const rows = [...container.querySelectorAll("[data-settings-index]")];
    expect(rows).toHaveLength(8);
    expect(rows[0].textContent).toContain("Top-K 4 · Vector 65%");
    expect(rows[1].textContent).toContain("Bật/tắt và mô hình xếp hạng");
    expect(rows[1].querySelector(".settings-dirty-dot")).not.toBeNull();

    await click(rows[2]);
    expect(onSelect).toHaveBeenCalledWith("gate");
  });

  it("nhóm của mục: #settings thuộc Hệ thống trả lời", () => {
    expect(settingsGroupOf(null)).toBe("answer");
    expect(settingsGroupOf("gate")).toBe("answer");
    expect(settingsGroupOf("models-llm")).toBe("models");
    expect(settingsGroupOf("appearance")).toBe("personal");
  });
});

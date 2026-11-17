import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SettingsIndex, SettingsSidebar } from "./SettingsNav";

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

  async function click(element) {
    await act(async () => {
      element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
  }

  it("cột danh mục có ba nhóm, tám mục và hash riêng", async () => {
    await render(<SettingsSidebar activeKey="gate" onSelect={() => {}} />);

    const groups = [...container.querySelectorAll(".settings-nav-group-title")].map((item) =>
      item.textContent.trim()
    );
    expect(groups).toEqual(["Hệ thống trả lời", "Mô hình", "Cá nhân"]);

    const items = [...container.querySelectorAll("[data-settings-nav]")];
    expect(items.map((item) => item.getAttribute("href"))).toEqual([
      "#settings/retrieval",
      "#settings/reranker",
      "#settings/gate",
      "#settings/generation",
      "#settings/models-llm",
      "#settings/models-embedding",
      "#settings/models-reranker",
      "#settings/appearance",
    ]);
    expect(container.querySelector('[data-settings-nav="gate"]').getAttribute("aria-current")).toBe(
      "location"
    );
    expect(
      container.querySelector('[data-settings-nav="models-llm"]').getAttribute("aria-current")
    ).toBeNull();
  });

  it("mục có thay đổi chưa lưu hiện chấm", async () => {
    await render(
      <SettingsSidebar activeKey="retrieval" dirtySections={["retrieval", "gate"]} onSelect={() => {}} />
    );

    expect(container.querySelector('[data-settings-nav="retrieval"] .settings-dirty-dot')).not.toBeNull();
    expect(container.querySelector('[data-settings-nav="gate"] .settings-dirty-dot')).not.toBeNull();
    expect(container.querySelector('[data-settings-nav="reranker"] .settings-dirty-dot')).toBeNull();
    expect(container.querySelector('[data-settings-nav="retrieval"]').getAttribute("aria-current")).toBe(
      "location"
    );
  });

  it("bấm mục gọi onSelect với key", async () => {
    const onSelect = vi.fn();
    await render(<SettingsSidebar activeKey="retrieval" onSelect={onSelect} />);

    await click(container.querySelector('[data-settings-nav="models-embedding"]'));

    expect(onSelect).toHaveBeenCalledWith("models-embedding");
  });

  it("danh sách mobile hiện mô tả và gọi onSelect", async () => {
    const onSelect = vi.fn();
    await render(<SettingsIndex dirtySections={["reranker"]} onSelect={onSelect} />);

    const rows = [...container.querySelectorAll("[data-settings-index]")];
    expect(rows).toHaveLength(8);
    expect(rows[1].textContent).toContain("Bật/tắt và mô hình xếp hạng");
    expect(rows[1].querySelector(".settings-dirty-dot")).not.toBeNull();

    await click(rows[2]);
    expect(onSelect).toHaveBeenCalledWith("gate");
  });
});

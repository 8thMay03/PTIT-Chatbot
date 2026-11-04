import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DatasetCard from "./DatasetCard";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("DatasetCard", () => {
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

  it("mọi dataset đều có mục Xóa, kể cả dataset `default` cũ", () => {
    const onDelete = vi.fn();
    act(() => {
      root.render(
        <DatasetCard
          dataset={{ id: "default", name: "Mặc định", enabled: true, document_count: 3, chunk_count: 9 }}
          onDelete={onDelete}
        />,
      );
    });

    act(() => container.querySelector(".dataset-menu-btn").click());
    const deleteItem = [...container.querySelectorAll('[role="menuitem"]')].find(
      (item) => item.textContent === "Xóa",
    );

    expect(deleteItem).toBeTruthy();
    act(() => deleteItem.click());
    expect(onDelete).toHaveBeenCalledTimes(1);
  });
});

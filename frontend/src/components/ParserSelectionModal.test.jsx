import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ParserSelectionModal, { parserBaseName, parserTitle } from "./ParserSelectionModal";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const PARSERS = [
  { name: "docling", is_default: true },
  {
    name: "llamaparse",
    is_default: false,
    variants: ["fast", "cost_effective", "agentic", "agentic_plus"],
    default_variant: "cost_effective",
  },
];

describe("ParserSelectionModal", () => {
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

  function renderUpload(onConfirm) {
    act(() => {
      root.render(<ParserSelectionModal upload={{ files: [{ name: "so-tay.pdf" }], parsers: PARSERS, choiceCount: 1 }}
        onClose={() => {}} onConfirm={onConfirm} />);
    });
  }

  const confirmButton = () => [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Tải lên và parse"));
  const click = (element) => act(() => element.click());

  it("shows LlamaParse tiers only when LlamaParse is selected and sends the chosen tier", () => {
    const onConfirm = vi.fn();
    renderUpload(onConfirm);
    expect(document.querySelector(".parser-variants")).toBeNull();

    click(confirmButton());
    expect(onConfirm).toHaveBeenLastCalledWith("docling");

    click(document.querySelector("input[value='llamaparse']"));
    const tiers = [...document.querySelectorAll(".parser-variants input")].map((input) => input.value);
    expect(tiers).toEqual(["fast", "cost_effective", "agentic", "agentic_plus"]);
    expect(document.querySelector(".parser-variants input:checked").value).toBe("cost_effective");
    expect(document.querySelector(".parser-variants").textContent).toContain("45 credit/trang");

    click(confirmButton());
    expect(onConfirm).toHaveBeenLastCalledWith("llamaparse:cost_effective");

    click(document.querySelector("input[value='agentic_plus']"));
    click(confirmButton());
    expect(onConfirm).toHaveBeenLastCalledWith("llamaparse:agentic_plus");
  });

  it("formats parser names that carry a tier", () => {
    expect(parserTitle("llamaparse:agentic")).toBe("LlamaParse · Agentic");
    expect(parserTitle("docling")).toBe("Docling");
    expect(parserBaseName("llamaparse:fast")).toBe("llamaparse");
    expect(parserBaseName("docling")).toBe("docling");
  });
});

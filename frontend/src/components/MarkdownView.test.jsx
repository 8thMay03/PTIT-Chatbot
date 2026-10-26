import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import MarkdownView from "./MarkdownView";

function parse(html) {
  const container = document.createElement("div");
  container.innerHTML = html;
  return container;
}

describe("MarkdownView", () => {
  it("render Markdown đã sanitize và chip trích dẫn", () => {
    const container = parse(
      renderToStaticMarkup(
        <MarkdownView
          className="md"
          content={"Xem [1] nhé."}
          sources={[{ citation_id: 1, locator: 'Mục " onfocus="alert(1)' }]}
        />
      )
    );
    const chip = container.querySelector("button.citation-chip");

    expect(container.querySelector("div.md")).not.toBeNull();
    expect(chip).not.toBeNull();
    expect(chip.getAttribute("data-citation-id")).toBe("1");
    expect(container.querySelector("[onfocus]")).toBeNull();
  });

  it("không render thẻ thực thi từ nội dung", () => {
    const container = parse(
      renderToStaticMarkup(
        <MarkdownView content={'<img src="x"/onerror="alert(1)">\n\n<script>alert(2)</script>'} />
      )
    );

    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    for (const element of container.querySelectorAll("*")) {
      for (const attr of element.attributes) {
        expect(attr.name.toLowerCase()).not.toMatch(/^on/);
      }
    }
  });
});

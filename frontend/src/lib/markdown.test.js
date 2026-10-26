import { describe, expect, it } from "vitest";
import { renderMarkdownHtml } from "./markdown";

function parse(html) {
  const container = document.createElement("div");
  container.innerHTML = html;
  return container;
}

const UNSAFE_TAGS = [
  "script",
  "iframe",
  "img",
  "svg",
  "math",
  "object",
  "embed",
  "style",
  "form",
  "input",
  "video",
  "audio",
  "link",
  "meta",
];

const DANGEROUS_URL = /^\s*(?:javascript|vbscript|data):/i;

function expectNoExecutableMarkup(container) {
  for (const tag of UNSAFE_TAGS) {
    expect(container.querySelector(tag), `còn thẻ <${tag}>`).toBeNull();
  }

  for (const element of container.querySelectorAll("*")) {
    for (const attr of element.attributes) {
      const name = attr.name.toLowerCase();
      expect(name, `<${element.tagName}> còn thuộc tính ${name}`).not.toMatch(/^on/);
      if (["href", "src", "action", "formaction", "xlink:href", "data"].includes(name)) {
        expect(DANGEROUS_URL.test(attr.value), `URL nguy hiểm: ${attr.value}`).toBe(false);
      }
    }
  }
}

const XSS_PAYLOADS = [
  "<img src=\"x\"/onerror=\"alert(1)\">",
  "<iframe src=\"javascript:alert(2)\">",
  '<a href="&#106;avascript:alert(3)">bấm</a>',
  '<svg onload="alert(4)"></svg>',
  "<math><mtext><script>alert(5)</script></mtext></math>",
  "[bấm](javascript:alert(6))",
  '<a href="jav&#x61;script:alert(7)">bấm</a>',
  '<div onclick="alert(8)">chữ</div>',
  "<img src=x onerror=alert(9)>",
  '<a href="jAvAsCrIpT:alert(10)">bấm</a>',
  "<iframe src=javascript:alert(11)>",
  "<style>body { display: none }</style>",
  '<object data="javascript:alert(13)"></object>',
  '<embed src="javascript:alert(14)">',
  '<a href="data:text/html,<script>alert(15)</script>">bấm</a>',
  "[bấm](vbscript:alert(16))",
  '<p style="background: url(javascript:alert(18))">chữ</p>',
  '<form action="javascript:alert(19)"><input onfocus="alert(19)" autofocus></form>',
  '<svg><animate onbegin="alert(20)" attributeName="x" dur="1s"></animate></svg>',
  '<a href="https://example.com" onmouseover="alert(21)">bấm</a>',
  "[bấm](&#106;avascript:alert(22))",
  "[bấm](data:text/html,<script>alert(23)</script>)",
  '[bấm](JaVaScRiPt:alert(24))',
];

describe("renderMarkdownHtml – chặn XSS", () => {
  it.each(XSS_PAYLOADS)("payload %#: %s", (payload) => {
    const container = parse(renderMarkdownHtml(payload));
    expectNoExecutableMarkup(container);
  });

  it("chặn ảnh Markdown", () => {
    const container = parse(renderMarkdownHtml("![mô tả](https://example.com/x.png)"));
    expect(container.querySelector("img")).toBeNull();
  });

  it("thẻ HTML thô trong bảng cũng bị lọc thuộc tính", () => {
    const html = renderMarkdownHtml(
      '<table><tr><th colspan="2" onclick="alert(1)">Mục</th></tr>' +
        '<tr><td onmouseover="alert(2)">1</td><td><iframe src="javascript:alert(3)"></iframe>2</td></tr></table>'
    );
    const container = parse(html);

    expect(container.querySelector("div.doc-table-wrapper > table.doc-table")).not.toBeNull();
    expect(container.querySelector("th").getAttribute("colspan")).toBe("2");
    expect(container.querySelector("[onclick]")).toBeNull();
    expect(container.querySelector("[onmouseover]")).toBeNull();
    expect(container.querySelector("iframe")).toBeNull();
  });

  it("chỉ giữ link http/https/mailto và thêm rel an toàn", () => {
    const container = parse(
      renderMarkdownHtml(
        "[an toàn](https://example.com)\n\n[thư](mailto:abc@example.com)\n\n[không](javascript:alert(1))"
      )
    );
    const links = Array.from(container.querySelectorAll("a"));

    expect(links).toHaveLength(2);
    for (const link of links) {
      expect(link.getAttribute("target")).toBe("_blank");
      expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    }
    expect(links[0].getAttribute("href")).toBe("https://example.com");
    expect(links[1].getAttribute("href")).toBe("mailto:abc@example.com");
    expect(container.textContent).toContain("[không](javascript:alert(1))");
  });
});

describe("renderMarkdownHtml – chip trích dẫn", () => {
  it("biến [n] thành chip và escape nhãn từ backend", () => {
    const sources = [{ citation_id: 1, locator: 'Mục " onfocus="alert(1)' }];
    const html = renderMarkdownHtml("Xem [1] nhé.", sources);
    const container = parse(html);
    const chip = container.querySelector("button.citation-chip");

    expect(chip).not.toBeNull();
    expect(chip.getAttribute("data-citation-id")).toBe("1");
    expect(chip.getAttribute("aria-label")).toBe(
      'Xem nguồn trích dẫn số 1: Mục " onfocus="alert(1)'
    );
    expect(container.querySelector("[onfocus]")).toBeNull();
    expect(html).toContain("&quot;");
  });

  it("heading chứa dấu nháy kép không tạo thuộc tính mới", () => {
    const sources = [{ citation_id: 1, locator: 'Tiêu đề " onfocus="alert(1)' }];
    const html = renderMarkdownHtml('## Tiêu đề " onfocus="alert(1) [1]', sources);
    const container = parse(html);

    expect(container.querySelector("h2.doc-h2")).not.toBeNull();
    expect(container.querySelector("[onfocus]")).toBeNull();
    expect(container.querySelectorAll("*").length).toBeGreaterThan(0);
    expect(container.querySelector("button.citation-chip")).not.toBeNull();
    expect(container.textContent).toContain('Tiêu đề " onfocus="alert(1)');
  });

  it("không tạo chip khi không có nguồn hoặc nằm trong code", () => {
    expect(renderMarkdownHtml("Xem [1].")).toContain("[1]");

    const sources = [{ citation_id: 1, locator: "Mục" }];
    const container = parse(renderMarkdownHtml("`[1]` và [1]", sources));
    expect(container.querySelector("code").textContent).toBe("[1]");
    expect(container.querySelectorAll("button.citation-chip")).toHaveLength(1);
  });

  it("escape nhãn chứa HTML", () => {
    const sources = [{ citation_id: 2, section_path: '"><img src=x onerror=alert(1)>' }];
    const container = parse(renderMarkdownHtml("Xem [2].", sources));

    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("[onerror]")).toBeNull();
    expect(container.querySelector("button.citation-chip").getAttribute("aria-label")).toContain(
      '"><img src=x onerror=alert(1)>'
    );
  });
});

describe("renderMarkdownHtml – lỗi hiển thị", () => {
  it("danh sách đánh số có dòng trống vẫn là một danh sách", () => {
    const container = parse(
      renderMarkdownHtml("1. Mục một\n\n2. Mục hai\n\n3. Mục ba")
    );

    expect(container.querySelectorAll("ol")).toHaveLength(1);
    expect(container.querySelectorAll("ol > li")).toHaveLength(3);
    expect(container.textContent).not.toMatch(/1\.\s*1\./);
    expect(container.querySelectorAll("ol > li")[2].textContent).toContain("Mục ba");
  });

  it("giữ đúng cấp của danh sách lồng nhau", () => {
    const container = parse(
      renderMarkdownHtml("- Cấp một\n  - Cấp hai a\n  - Cấp hai b\n- Cấp một b")
    );

    expect(container.querySelectorAll("ul")).toHaveLength(2);
    expect(container.querySelector("ul > li > ul")).not.toBeNull();
    expect(container.querySelectorAll("ul > li > ul > li")).toHaveLength(2);
  });

  it("hiển thị khối code ba dấu backtick", () => {
    const html = renderMarkdownHtml(
      '```js\nconst a = 1;\nif (a < 2) { console.log("**x**"); }\n```'
    );
    const container = parse(html);
    const code = container.querySelector("pre.doc-pre > code.doc-code-block");

    expect(code).not.toBeNull();
    expect(code.textContent).toContain("const a = 1;");
    expect(code.textContent).toContain('console.log("**x**")');
    expect(code.querySelector("strong")).toBeNull();
    expect(code.textContent).not.toContain("```");
  });

  it("không xử lý ** bên trong inline code", () => {
    const container = parse(renderMarkdownHtml("Giữ `**nguyên**` và `a < b`."));
    const codes = container.querySelectorAll("code.doc-inline-code");

    expect(codes).toHaveLength(2);
    expect(codes[0].textContent).toBe("**nguyên**");
    expect(codes[0].querySelector("strong")).toBeNull();
    expect(codes[1].textContent).toBe("a < b");
  });

  it("bảng pipe và bảng HTML đều có class giao diện", () => {
    const pipe = parse(
      renderMarkdownHtml("| Mục | Nội dung |\n| --- | --- |\n| A | B |\n| C | D |")
    );
    expect(pipe.querySelector("div.doc-table-wrapper > table.doc-table")).not.toBeNull();
    expect(pipe.querySelectorAll("thead th")).toHaveLength(2);
    expect(pipe.querySelectorAll("tbody tr")).toHaveLength(2);

    const htmlTable = parse(
      renderMarkdownHtml(
        "<table><thead><tr><th>Mục</th><th>Nội dung</th></tr></thead>" +
          "<tbody><tr><td>A</td><td>B</td></tr><tr><td>C</td><td>D</td></tr></tbody></table>"
      )
    );
    expect(htmlTable.querySelector("div.doc-table-wrapper > table.doc-table")).not.toBeNull();
    expect(htmlTable.querySelectorAll("tbody tr")).toHaveLength(2);
  });

  it("giữ class doc-p cho đoạn văn và doc-h cho heading", () => {
    const container = parse(renderMarkdownHtml("# Tiêu đề\n\nMột đoạn văn."));

    expect(container.querySelector("h1.doc-h1")).not.toBeNull();
    expect(container.querySelector("p.doc-p")).not.toBeNull();
  });
});

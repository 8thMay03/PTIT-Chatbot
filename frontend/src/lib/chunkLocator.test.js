import { describe, expect, it } from "vitest";
import { renderMarkdownHtml } from "./markdown";
import { createChunkLocator, locateChunk, buildDocumentIndex, normalizeForMatch } from "./chunkLocator";

function renderDoc(markdown) {
  const root = document.createElement("div");
  root.innerHTML = renderMarkdownHtml(markdown);
  return root;
}

const texts = (elements) => elements.map((el) => el.textContent.replace(/\s+/g, " ").trim());

describe("normalizeForMatch", () => {
  it("keeps only letters and digits, lowercased", () => {
    expect(normalizeForMatch("  Điều 5. Học phí — **HK1**!")).toBe("điều5họcphíhk1");
  });
});

describe("locateChunk", () => {
  it("finds table rows written with pipes, <br/> and escapes", () => {
    const root = renderDoc(
      [
        "## Khoa Viễn thông",
        "",
        "Danh sách lãnh đạo khoa.",
        "",
        "|ĐƠN VỊ|HỌ VÀ TÊN|EMAIL|",
        "|-|-|-|",
        "|Lãnh đạo<br/>Khoa|PGS.TS. Đặng Thế Ngọc|ngocdt\\@ptit.edu.vn|",
        "|BM Mạng<br/>viễn thông|PGS.TS. Hoàng Trọng<br/>Minh|minh\\@ptit.edu.vn|",
        "",
        "## Khoa Kế toán",
        "",
        "Nội dung khác.",
      ].join("\n")
    );
    const chunk = [
      "## Khoa Viễn thông",
      "",
      "|ĐƠN VỊ|HỌ VÀ TÊN|EMAIL|",
      "|-|-|-|",
      "|BM Mạng<br/>viễn thông|PGS.TS. Hoàng Trọng<br/>Minh|minh\\@ptit.edu.vn|",
    ].join("\n");

    const result = locateChunk(buildDocumentIndex(root), chunk);

    expect(result).not.toBeNull();
    expect(texts(result.elements).at(-1)).toContain("Hoàng Trọng");
    expect(texts(result.elements).join(" ")).not.toContain("Khoa Kế toán");
  });

  it("marks only the body of a later child, not the section heading copied into it", () => {
    const body = Array.from({ length: 6 }, (_, i) => `${i + 1}. Khoản số ${i + 1} quy định nội dung riêng thứ ${i + 1} của điều này.`);
    const root = renderDoc(["##### Điều 7. Học phí", "", ...body.map((line) => `${line}\n`)].join("\n"));
    const index = buildDocumentIndex(root);

    const firstChild = locateChunk(index, ["##### Điều 7. Học phí", "", body[0], "", body[1]].join("\n"));
    const laterChild = locateChunk(index, ["##### Điều 7. Học phí", "", body[4], "", body[5]].join("\n"));

    expect(texts(firstChild.elements)[0]).toBe("Điều 7. Học phí");
    expect(texts(laterChild.elements)).toEqual([
      "Khoản số 5 quy định nội dung riêng thứ 5 của điều này.",
      "Khoản số 6 quy định nội dung riêng thứ 6 của điều này.",
    ]);
  });

  it("does not stitch together pieces of two similar places", () => {
    const root = renderDoc(
      [
        "c) Loại 3:",
        "",
        "i) Học phí chuyên ngành: Miễn 50% học phí toàn khóa.",
        "",
        "ii) Các chế độ khác áp dụng như các điểm ii, iii, iv mục a.",
        "",
        "d) Loại 4:",
        "",
        "i) Học phí chuyên ngành: Miễn 100% học phí toàn khóa.",
        "",
        "ii) Các chế độ khác áp dụng như các điểm iii, vi mục a.",
        "",
        "e) Loại 5:",
        "",
        "i) Học phí chuyên ngành: Miễn 50% học phí toàn khóa.",
        "",
        "ii) Các chế độ khác áp dụng như các điểm iii, vi mục a.",
      ].join("\n")
    );
    const chunk = [
      "i) Học phí chuyên ngành: Miễn 50% học phí toàn khóa.",
      "",
      "ii) Các chế độ khác áp dụng như các điểm iii, vi mục a.",
    ].join("\n");

    const result = locateChunk(buildDocumentIndex(root), chunk, { hintRatio: 0 });

    expect(result.elements).toHaveLength(2);
    expect(result.elements[0].previousElementSibling.textContent).toBe("e) Loại 5:");
  });

  it("returns null instead of guessing when the chunk text is not in the document", () => {
    const root = renderDoc("# Tiêu đề\n\nMột đoạn văn bản bất kỳ trong tài liệu.");
    expect(locateChunk(buildDocumentIndex(root), "Nội dung hoàn toàn không có trong tài liệu này.")).toBeNull();
  });
});

describe("createChunkLocator", () => {
  const program = (name) =>
    [
      `### Ngành ${name}`,
      "",
      `Giới thiệu riêng của ngành ${name} với nội dung đủ dài để phân biệt.`,
      "",
      "#### NĂM HỌC THỨ BA",
      "",
      "|TT|Tên học phần|Số TC|",
      "|-|-|-|",
      "|1|Tư tưởng Hồ Chí Minh|2|",
      "|2|Kinh doanh quốc tế|3|",
      "|3|Kinh tế lượng|3|",
      "",
    ].join("\n");

  it("places identical content after the previous chunk in the list", () => {
    const root = renderDoc([program("Marketing"), program("Thương mại điện tử")].join("\n"));
    const table = ["#### NĂM HỌC THỨ BA", "", "|TT|Tên học phần|Số TC|", "|-|-|-|", "|1|Tư tưởng Hồ Chí Minh|2|", "|2|Kinh doanh quốc tế|3|", "|3|Kinh tế lượng|3|"].join("\n");
    const list = [
      { id: "a", chunk_index: 2, text: "### Ngành Thương mại điện tử\n\nGiới thiệu riêng của ngành Thương mại điện tử với nội dung đủ dài để phân biệt." },
      { id: "b", chunk_index: 3, text: table },
    ];
    const locator = createChunkLocator(root);

    // Ước lượng theo tỷ lệ trỏ về bản đầu; đoạn liền trước kéo về đúng bản thứ hai.
    const found = locator.locate(list, 1, 1000);

    const rows = Array.from(root.querySelectorAll("tr"));
    expect(found).toContain(rows[rows.length - 1]);
    expect(found).not.toContain(rows[3]);
  });

  it("returns an empty list for a position outside the list", () => {
    const locator = createChunkLocator(renderDoc("Văn bản."));
    expect(locator.locate([], 0, 0)).toEqual([]);
  });
});

import { describe, expect, it, vi } from "vitest";
import { conversationsToMarkdown, exportFileName, fetchAllConversations } from "./exportConversations";

function fakeApi(total, { pageLimit } = {}) {
  const all = Array.from({ length: total }, (_, index) => ({ id: `c-${index}`, title: `Hội thoại ${index}` }));
  let inFlight = 0;
  let maxInFlight = 0;
  const api = {
    list: vi.fn(async ({ limit, offset }) => ({
      total,
      conversations: all.slice(offset, offset + Math.min(limit, pageLimit ?? limit)),
    })),
    get: vi.fn(async (id) => {
      inFlight += 1;
      maxInFlight = Math.max(maxInFlight, inFlight);
      await new Promise((resolve) => setTimeout(resolve, 1));
      inFlight -= 1;
      return { id, title: id, messages: [] };
    }),
  };
  return { api, maxInFlight: () => maxInFlight };
}

describe("fetchAllConversations", () => {
  it("phân trang danh sách, tải chi tiết song song có giới hạn, giữ thứ tự", async () => {
    const { api, maxInFlight } = fakeApi(7);
    const progress = vi.fn();

    const details = await fetchAllConversations(api, { pageSize: 3, onProgress: progress });

    expect(api.list.mock.calls.map(([options]) => options.offset)).toEqual([0, 3, 6]);
    expect(details.map((item) => item.id)).toEqual(["c-0", "c-1", "c-2", "c-3", "c-4", "c-5", "c-6"]);
    expect(maxInFlight()).toBeLessThanOrEqual(4);
    expect(progress).toHaveBeenLastCalledWith(7, 7);
  });

  it("không có hội thoại thì không gọi chi tiết", async () => {
    const { api } = fakeApi(0);
    expect(await fetchAllConversations(api)).toEqual([]);
    expect(api.get).not.toHaveBeenCalled();
  });

  it("dừng khi trang trả rỗng dù total còn lớn hơn", async () => {
    const api = {
      list: vi.fn(async () => ({ total: 5, conversations: [] })),
      get: vi.fn(),
    };
    expect(await fetchAllConversations(api)).toEqual([]);
    expect(api.list).toHaveBeenCalledTimes(1);
  });
});

describe("conversationsToMarkdown", () => {
  it("gồm tiêu đề, câu hỏi, câu trả lời và nguồn trích dẫn", () => {
    const markdown = conversationsToMarkdown(
      [
        {
          id: "c-1",
          title: "Học phí",
          created_at: "2026-11-01T08:00:00Z",
          messages: [
            { role: "user", content: "Học phí tính thế nào?" },
            {
              role: "assistant",
              content: "Theo tín chỉ [1].",
              sources: [
                {
                  citation_id: 1,
                  locator: "Điều 5",
                  source_name: "Sổ tay sinh viên",
                  section_path: "Chương II > Điều 5",
                },
              ],
            },
            { role: "user", content: "Còn gì nữa?" },
            { role: "assistant", content: "", interrupted: true, sources: [] },
          ],
        },
      ],
      { exportedAt: new Date("2026-11-17T10:00:00Z") }
    );

    expect(markdown).toContain("# Lịch sử hội thoại — PTIT Chatbot");
    expect(markdown).toContain("1 hội thoại.");
    expect(markdown).toContain("## Học phí");
    expect(markdown).toContain("### Câu hỏi\n\nHọc phí tính thế nào?");
    expect(markdown).toContain("### Trả lời\n\nTheo tín chỉ [1].");
    expect(markdown).toContain("- [1] Điều 5 — Sổ tay sinh viên — Chương II > Điều 5");
    expect(markdown).toContain("_Đã dừng trước khi có câu trả lời._");
  });
});

describe("exportFileName", () => {
  it("ghi ngày theo giờ máy", () => {
    expect(exportFileName(new Date(2026, 10, 7))).toBe("ptit-chatbot-lich-su-2026-11-07.md");
  });
});

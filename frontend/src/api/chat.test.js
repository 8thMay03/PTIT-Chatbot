import { afterEach, describe, expect, it, vi } from "vitest";
import { streamChat } from "./chat";

function ndjsonResponse(events) {
  const encoder = new TextEncoder();
  const body = new ReadableStream({
    start(controller) {
      events.forEach((event) => controller.enqueue(encoder.encode(`${JSON.stringify(event)}\n`)));
      controller.close();
    },
  });
  return Promise.resolve({ ok: true, status: 200, headers: { get: () => "application/x-ndjson" }, body });
}

async function drain(iterator) {
  const events = [];
  for await (const event of iterator) events.push(event);
  return events;
}

describe("streamChat", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("không gửi top_k khi không truyền để server dùng mặc định admin cấu hình", async () => {
    const fetchMock = vi.fn(() => ndjsonResponse([{ type: "start", conversation_id: "c-1" }]));
    vi.stubGlobal("fetch", fetchMock);

    const events = await drain(streamChat({ message: "Học phí?" }));

    expect(events).toEqual([{ type: "start", conversation_id: "c-1" }]);
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body).toEqual({ message: "Học phí?", conversation_id: null });
    expect("top_k" in body).toBe(false);
  });

  it("vẫn gửi top_k khi caller truyền số", async () => {
    const fetchMock = vi.fn(() => ndjsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await drain(streamChat({ message: "Học phí?", conversationId: "c-1", topK: 6 }));

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      message: "Học phí?",
      conversation_id: "c-1",
      top_k: 6,
    });
  });
});

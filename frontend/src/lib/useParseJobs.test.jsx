import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import useParseJobs from "./useParseJobs";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function jsonResponse(payload) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(payload),
  });
}

function job(status) {
  return {
    id: "job-1",
    kind: "parse",
    status,
    document_id: "doc-1",
    file_name: "policy.pdf",
    parser_name: null,
    created_at: "2026-10-27T14:00:00Z",
    started_at: "2026-10-27T14:00:01Z",
    finished_at: status === "succeeded" ? "2026-10-27T14:00:02Z" : null,
    error: null,
    result:
      status === "succeeded"
        ? {
            id: "doc-1",
            title: "policy",
            file_name: "policy.pdf",
            source_path: "data/policy.pdf",
            status: "parsed",
            parsed_at: "2026-10-27T14:00:02Z",
            chunk_count: 0,
          }
        : null,
  };
}

function Harness({ onFinished }) {
  const { jobs } = useParseJobs({ onFinished, pollIntervalMs: 10 });
  return <span data-job-count={jobs.length}>{jobs.length}</span>;
}

describe("useParseJobs", () => {
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
    vi.unstubAllGlobals();
  });

  it("reports a job that transitions from running to succeeded", async () => {
    let calls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(() => {
        calls += 1;
        return jsonResponse({ jobs: [job(calls === 1 ? "running" : "succeeded")] });
      })
    );
    const onFinished = vi.fn();

    await act(async () => {
      root.render(<Harness onFinished={onFinished} />);
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    await vi.waitFor(() => expect(onFinished).toHaveBeenCalledTimes(1), { timeout: 1000 });

    expect(onFinished.mock.calls[0][0]).toMatchObject({
      id: "job-1",
      status: "succeeded",
      result: { file_name: "policy.pdf" },
    });
    expect(container.textContent).toBe("0");
  });
});

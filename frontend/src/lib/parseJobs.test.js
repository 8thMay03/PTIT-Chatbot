import { describe, expect, it } from "vitest";
import { isActiveParseJob, parseJobLabel } from "./parseJobs";

describe("parse job helpers", () => {
  it("treats queued and running jobs as active", () => {
    expect(isActiveParseJob({ status: "queued" })).toBe(true);
    expect(isActiveParseJob({ status: "running" })).toBe(true);
    expect(isActiveParseJob({ status: "succeeded" })).toBe(false);
    expect(isActiveParseJob({ status: "failed" })).toBe(false);
    expect(isActiveParseJob(null)).toBe(false);
  });

  it("prefers the returned document name, then the uploaded file name", () => {
    expect(parseJobLabel({ file_name: "policy.pdf" })).toBe("policy.pdf");
    expect(parseJobLabel({ file_name: "old.pdf", result: { file_name: "new.pdf" } })).toBe("new.pdf");
    expect(parseJobLabel(null)).toBe("tài liệu");
  });
});

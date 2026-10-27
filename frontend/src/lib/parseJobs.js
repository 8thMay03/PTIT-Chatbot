export const ACTIVE_PARSE_JOB_STATUSES = ["queued", "running"];

/** A background parse is still waiting in the queue or running. */
export function isActiveParseJob(job) {
  return Boolean(job) && ACTIVE_PARSE_JOB_STATUSES.includes(job.status);
}

/** Human label used in banners/toasts before the job returns a document. */
export function parseJobLabel(job) {
  return job?.result?.file_name || job?.file_name || "tài liệu";
}

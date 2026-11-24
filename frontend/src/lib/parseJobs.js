export const ACTIVE_PARSE_JOB_STATUSES = ["queued", "running"];

/** A background parse is still waiting in the queue or running. */
export function isActiveParseJob(job) {
  return Boolean(job) && ACTIVE_PARSE_JOB_STATUSES.includes(job.status);
}

/** Human label used in banners/toasts before the job returns a document. */
export function parseJobLabel(job) {
  return job?.result?.file_name || job?.file_name || "tài liệu";
}

/** Job nền nhúng lại vector (cùng hàng đợi/endpoint với job parse). */
export function isEmbedJob(job) {
  return job?.kind === "embed";
}

/** Job embed thuộc dataset này: job của dataset, của một tài liệu trong dataset, hoặc toàn kho. */
export function embedJobCoversDataset(job, datasetId) {
  if (!isEmbedJob(job)) return false;
  if (!job.dataset_id && !job.document_id) return true;
  return job.dataset_id === datasetId;
}

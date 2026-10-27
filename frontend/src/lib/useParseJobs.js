import { useCallback, useEffect, useRef, useState } from "react";
import { documentsApi } from "../api";
import { isActiveParseJob } from "./parseJobs";

const POLL_INTERVAL_MS = 1200;

/**
 * Theo dõi job parse chạy nền.
 *
 * Job state nằm ở backend, không phải state của màn hình: khi người dùng rời
 * trang rồi quay lại, hook tải lại các job đang chạy. Polling chỉ bật khi còn
 * job `queued`/`running` để không gọi API liên tục lúc rảnh.
 */
export function useParseJobs({ onFinished, pollIntervalMs = POLL_INTERVAL_MS } = {}) {
  const [jobs, setJobs] = useState([]);
  const jobsRef = useRef([]);
  const handledRef = useRef(new Set());
  const onFinishedRef = useRef(onFinished);
  const pollingRef = useRef(false);

  onFinishedRef.current = onFinished;

  const replaceJobs = useCallback((next) => {
    jobsRef.current = next;
    setJobs(next);
  }, []);

  const finish = useCallback((job) => {
    if (!job || handledRef.current.has(job.id)) return;
    handledRef.current.add(job.id);
    onFinishedRef.current?.(job);
  }, []);

  /**
   * Gộp job server trả về. `replace` dùng cho polling: danh sách server là
   * nguồn sự thật, job active biến mất (ví dụ backend restart) cũng bị bỏ để
   * giao diện không quay vô hạn.
   */
  const applyJobs = useCallback(
    (incoming, { replace = false } = {}) => {
      const list = Array.isArray(incoming) ? incoming : incoming ? [incoming] : [];
      if (!list.length && !replace) return;

      const previous = jobsRef.current;
      const previousIds = new Set(previous.map((job) => job.id));
      const byId = new Map(replace ? [] : previous.map((job) => [job.id, job]));
      for (const job of list) byId.set(job.id, job);

      if (replace) {
        const returnedIds = new Set(list.map((job) => job.id));
        const now = Date.now();
        for (const job of previous) {
          if (returnedIds.has(job.id)) continue;
          // A poll can race with a just-enqueued job. Keep local jobs for a short
          // grace period; after that an absent job means the backend restarted or
          // pruned it, so drop it instead of spinning forever.
          const createdAt = Date.parse(job.created_at || "");
          if (Number.isFinite(createdAt) && now - createdAt < 10_000) {
            byId.set(job.id, job);
          }
        }
      }

      replaceJobs([...byId.values()].filter(isActiveParseJob));
      for (const job of list) {
        if (previousIds.has(job.id) && !isActiveParseJob(job)) finish(job);
      }
    },
    [finish, replaceJobs]
  );

  const track = useCallback(
    (incoming) => {
      const list = Array.isArray(incoming) ? incoming : incoming ? [incoming] : [];
      applyJobs(list);
      // Job rất nhanh có thể đã xong ngay trong response enqueue.
      for (const job of list) {
        if (!isActiveParseJob(job)) finish(job);
      }
    },
    [applyJobs, finish]
  );

  // Nạp lại job đang chạy sau khi mở lại màn hình hoặc reload trang.
  useEffect(() => {
    let cancelled = false;
    documentsApi
      .parseJobs({ limit: 100 })
      .then((payload) => {
        if (!cancelled) applyJobs(payload.jobs ?? [], { replace: true });
      })
      .catch(() => {
        // Không có job hoặc API lỗi tạm thời: để lần poll sau xử lý.
      });
    return () => {
      cancelled = true;
    };
  }, [applyJobs]);

  useEffect(() => {
    if (jobs.length === 0) return undefined;
    let cancelled = false;
    const tick = async () => {
      if (pollingRef.current) return;
      pollingRef.current = true;
      try {
        const payload = await documentsApi.parseJobs({ limit: 100 });
        if (!cancelled) applyJobs(payload.jobs ?? [], { replace: true });
      } catch {
        // Lỗi mạng tạm thời: giữ trạng thái cũ và thử lại ở vòng sau.
      } finally {
        pollingRef.current = false;
      }
    };
    const timer = setInterval(tick, pollIntervalMs);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [jobs.length, applyJobs, pollIntervalMs]);

  return { jobs, track };
}

export default useParseJobs;

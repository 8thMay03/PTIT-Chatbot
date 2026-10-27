import React from "react";

function clampProgress(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, Math.min(100, Math.round(number)));
}

/** Thanh tiến trình dùng chung cho banner job nền, bảng tài liệu và màn chi tiết. */
export default function ParseProgress({
  progress,
  message,
  label = "Tiến trình parse",
  compact = false,
  indeterminate = false,
}) {
  const value = clampProgress(progress);
  const waiting = indeterminate && value === 0;

  return (
    <div
      className={`parse-progress ${compact ? "is-compact" : ""} ${waiting ? "is-indeterminate" : ""}`}
      title={message || undefined}
    >
      <div className="parse-progress-head">
        <span className="parse-progress-label">{label}</span>
        <span className="parse-progress-value">{waiting ? "Chờ" : `${value}%`}</span>
      </div>
      <div
        className="parse-progress-track"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={waiting ? undefined : value}
        aria-busy={waiting || undefined}
      >
        <span
          className="parse-progress-fill"
          style={waiting ? undefined : { width: `${value}%` }}
        />
      </div>
      {!compact && message ? <span className="parse-progress-message">{message}</span> : null}
    </div>
  );
}

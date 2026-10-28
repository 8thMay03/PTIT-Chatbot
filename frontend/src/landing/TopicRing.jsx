import React from "react";
import { RING_TOPICS } from "./content";

/**
 * Vòng thẻ chủ đề 3D phía sau tiêu đề dải kêu gọi, xoay theo tiến độ cuộn
 * (`--progress` do useLandingMotion ghi lên phần tử `data-scrub`). Mỗi thẻ đặt
 * trên vòng bằng `rotateY(góc) translateZ(bán kính)`; chỉ để trang trí.
 */
export default function TopicRing() {
  const total = RING_TOPICS.length;
  return (
    <div className="lp-ring" data-scrub aria-hidden="true">
      <div className="lp-ring-track">
        {RING_TOPICS.map(({ label, icon: Icon, tone }, index) => (
          <span
            key={label}
            className={`lp-ring-item lp-tag is-${tone}`}
            style={{ "--angle": `${(360 / total) * index}deg` }}
          >
            <Icon size={18} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}

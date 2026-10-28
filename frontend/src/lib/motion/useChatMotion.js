import { useLayoutEffect } from "react";
import { motionEnabled } from "./env";
import { setupClicks, setupPointer } from "./interactions";

/**
 * Chuyển động cần JS của trang chat: tilt/vệt sáng, sóng click, pixel transition
 * cho link (xem interactions.js). Phần còn lại là animation CSS chạy khi phần tử
 * mount (chat-motion.css). Gắn `.motion-ready` lên gốc để CSS chỉ bật các hiệu
 * ứng phụ thuộc JS khi đã gắn listener.
 */
export default function useChatMotion(rootRef) {
  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root || !motionEnabled()) return undefined;
    root.classList.add("motion-ready");
    const cleanups = [setupPointer(root), setupClicks(root)];
    return () => {
      cleanups.forEach((cleanup) => cleanup());
      root.classList.remove("motion-ready");
    };
  }, [rootRef]);
}

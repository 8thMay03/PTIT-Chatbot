import React, { Suspense, lazy } from "react";

const loadMarkdownView = () => import("./MarkdownView");
const MarkdownView = lazy(loadMarkdownView);

/**
 * Bắt đầu tải renderer Markdown (markdown-it + DOMPurify) ngay, không chờ lần render
 * đầu tiên. Gọi khi mở trang chat để chunk về gần như cùng lúc với màn chat.
 */
export function preloadMarkdownView() {
  return loadMarkdownView();
}

/**
 * MarkdownView tải lười cho trang chat: renderer Markdown nằm ở chunk riêng để JS
 * ban đầu của `/chat` nhỏ hơn (landing-user-auth, AC-06). Trong lúc chunk đang tải,
 * hiện nội dung dạng văn bản thuần — React tự escape nên không có HTML thô nào được
 * chèn trước khi qua DOMPurify.
 */
export default function LazyMarkdownView({ className = "", content, sources }) {
  return (
    <Suspense
      fallback={
        <div className={className}>
          <p className="doc-p markdown-pending">{content}</p>
        </div>
      }
    >
      <MarkdownView className={className} content={content} sources={sources} />
    </Suspense>
  );
}

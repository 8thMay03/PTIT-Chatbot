import React from "react";

/**
 * Tách chữ thành từng từ trong mặt nạ để trượt lên lần lượt (`--i` là thứ tự từ,
 * dùng làm độ trễ). Khoảng trắng giữa các từ là text node thật nên `textContent`
 * và tên truy cập của tiêu đề không đổi.
 */
export default function SplitWords({ text, start = 0 }) {
  const words = String(text).split(/\s+/).filter(Boolean);
  return words.map((word, index) => (
    <React.Fragment key={`${index}-${word}`}>
      {index > 0 && " "}
      <span className="lp-word" style={{ "--i": start + index }}>
        <span className="lp-word-inner">{word}</span>
      </span>
    </React.Fragment>
  ));
}

export function wordCount(text) {
  return String(text).split(/\s+/).filter(Boolean).length;
}

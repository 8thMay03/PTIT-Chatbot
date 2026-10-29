# Plan: 2026-10-29-md-editor-toggle-view

Nền: `dev` tại `c39bfef`. Một agent (`claude-agent`), nhánh `feat/md-editor-toggle-view`.

## Phân công

### S-01 — Gộp cột Markdown và nút chuyển chế độ

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: thay hai cột `raw`/`rendered` bằng cột `markdown` có trạng thái `markdownMode` (`raw` | `rendered`, luôn
  mở ở `raw`); nút trên header cột chuyển chế độ, giữ tỉ lệ cuộn; bỏ "Cuộn đồng bộ"; đổi khoá cột cũ trong
  `localStorage`; cập nhật test. Phục vụ `AC-01` … `AC-04`.
- Phạm vi file được sửa: `frontend/src/components/MarkdownEditorView.jsx`, `MarkdownEditorView.test.jsx`,
  `frontend/src/styles/markdown-editor.css`.
- Phụ thuộc: không.

## Hợp đồng dùng chung

- Không áp dụng: props của `MarkdownEditorView` giữ nguyên; khoá `localStorage` `ptit_md_editor_panes` giữ tên, giá
  trị nay là `original`/`markdown`.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; Reviewer: `claude-agent`; hình thức `self_review`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 → `npm test`, `build`, `check:bundle` → chụp màn hình bằng harness tạm với API giả → self-review.

## Rủi ro và điều chỉnh kế hoạch

- Mất lịch sử hoàn tác nếu gỡ textarea khi xem bản render → giữ textarea, chỉ ẩn bằng `hidden`.

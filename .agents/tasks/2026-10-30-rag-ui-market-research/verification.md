# Verification: 2026-10-30-rag-ui-market-research

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree trên `dev` (nền `04e3120`) với các file trong phạm vi task.
- Môi trường: Linux, Node 22.22.0, Vite 5 dev server, Playwright Chromium có sẵn.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: `claude-agent` / `2026-10-30T23:42:16+07:00`.
- Loại: kiểm tra thủ công + đối chiếu mã nguồn.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm ci`; `npx vite --port 5173`; script Playwright giả lập API, chụp ảnh. Đối chiếu từng
  `H-*` với file nêu trong bảng: `.sidebar { background: var(--brand-800) }` ở `styles/layout.css`;
  `.bubble-actions { opacity: 0 }` + `:hover` ở `styles/chat.css`; `Source` không có trường nội dung ở
  `schemas.py`; `/documents/{id}/file` và `/chunks` có `require_admin` ở `routes.py`; `grep -rn feedback
  backend/app` không có kết quả.
- Kỳ vọng: mỗi vấn đề có bằng chứng đúng.
- Kết quả thực tế: 13/13 vấn đề khớp mã nguồn/ảnh. Một nhận định nháp sai đã sửa trước khi chốt (xem dưới).
- Trạng thái: `passed`.
- Bằng chứng: `docs/design/assets/current-*.png`.

### V-02 — AC-02

- Loại: review tài liệu.
- Kết quả thực tế: 9 sản phẩm trong bảng §3.1 + chatbot sổ tay sinh viên; §10 có link cho mọi sản phẩm.
- Trạng thái: `passed`.

### V-03 — AC-03

- Loại: review tài liệu.
- Kết quả thực tế: bảng §5 có 12 đề xuất, mỗi đề xuất có ưu tiên, `H-*` liên quan, cột API; D-01, D-05 nêu
  fallback khi chưa có API; §6 tổng hợp thay đổi API đều là trường/endpoint tuỳ chọn.
- Trạng thái: `passed`.

### V-04 — AC-04

- Loại: kiểm tra thủ công.
- Lệnh / thao tác: mở `docs/design/mockups/chat-proposed.html` bằng Playwright 1366×820, chụp
  `docs/design/assets/proposed-chat-desktop.png`; xem ảnh.
- Kết quả thực tế: mockup hiện sidebar sáng, câu trả lời không bong bóng, hàng nguồn, popover trích dẫn, hàng
  hành động, câu hỏi liên quan, panel nguồn bên phải; §0 có bảng so sánh hiện tại/đề xuất.
- Trạng thái: `passed`.

### V-05 — AC-05

- Loại: review tài liệu.
- Kết quả thực tế: §8 nêu xung đột file với `2026-10-28-landing-user-auth`; §9 có 4 câu hỏi.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Bản nháp D-08 ghi "bỏ token `--accent` teal khỏi màn chat"; `grep var(--accent` cho thấy chỉ `config.css`,
  `dataset.css`, `document.css` dùng → đã sửa câu chữ.
- Chưa xác minh: ảnh chụp dark mode và màn chào mobile được chụp nhưng không đưa vào tài liệu; mockup chỉ có bản
  desktop sáng (mobile mô tả bằng chữ). Nhận định về Perplexity/ChatGPT/NotebookLM dựa trên nguồn bên thứ ba,
  không dùng thử trực tiếp.

## Kết luận

- Tiêu chí đã đạt: `AC-01` … `AC-05`.
- Tiêu chí chưa đạt: không có.
- Đề xuất: chờ người dùng phản hồi đề xuất.

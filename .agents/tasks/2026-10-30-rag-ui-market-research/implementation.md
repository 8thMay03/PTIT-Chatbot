# Implementation: 2026-10-30-rag-ui-market-research

## Tổng quan triển khai

Task tài liệu: không sửa mã nguồn ứng dụng. Nhánh `dev` (commit nền `04e3120`) theo chỉ định của phiên làm
việc; vì chỉ thêm tài liệu nên không tách nhánh `feat/…`.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-10-30T23:42:16+07:00`.
- Đã làm: đọc `App.jsx`, `ChatView.jsx`, `ReasoningPanel.jsx`, `ConversationList.jsx`, `MarkdownView.jsx`,
  `styles/tokens.css`, `styles/layout.css`, `styles/chat.css`, `backend/app/api/schemas.py`, `routes.py`,
  `generation/citations.py`. Chạy `npm ci` + Vite dev, script Playwright giả lập `/api/conversations` và
  `/api/chat/stream` (NDJSON với 4 bước + `done` có 2 nguồn) để chụp ảnh desktop 1366×820 sáng/tối và mobile
  390×844.
- File thay đổi: `docs/design/assets/current-welcome-desktop.png`, `current-answer-desktop.png`,
  `current-reasoning-desktop.png`, `current-answer-mobile.png`.
- Quyết định: script chụp ảnh để ở scratchpad, không đưa vào repo (công cụ dùng một lần).
- Kiểm tra đã chạy: xem `verification.md` V-01.

### S-02 — claude-agent

- Cập nhật lúc: `2026-10-30T23:42:16+07:00`.
- Đã làm: tìm kiếm web về Perplexity, ChatGPT search, NotebookLM, Onyx, Kotaemon, RAGFlow, Dify, Open WebUI,
  Kapa.ai, chatbot sổ tay sinh viên, Shape of AI, arXiv 2512.12207. WebFetch tới `arxiv.org` và
  `aiuxplayground.com` bị chặn (không phân giải được tên miền trong môi trường), nên dùng trích đoạn tìm kiếm.
- File thay đổi: `docs/design/RAG-UI-Market-Research.md` §3, §4, §10.

### S-03 — claude-agent

- Cập nhật lúc: `2026-10-30T23:42:16+07:00`.
- Đã làm: viết 12 đề xuất `D-01` … `D-12`, bảng thay đổi API, lộ trình 3 giai đoạn, phối hợp, câu hỏi mở;
  dựng mockup HTML tĩnh và chụp `proposed-chat-desktop.png`.
- File thay đổi: `docs/design/RAG-UI-Market-Research.md`, `docs/design/mockups/chat-proposed.html`,
  `docs/design/assets/proposed-chat-desktop.png`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: D-08 chạm `App.jsx` cùng task `2026-10-28-landing-user-auth`.

## Trao đổi giữa agents

### MSG-claude-agent-001

- Lúc: `2026-10-30T23:42:16+07:00`.
- Từ: `claude-agent` (task này); đến: coordinator task `2026-10-28-landing-user-auth`.
- Nhiệm vụ: `S-03`.
- Loại: `update`.
- Tham chiếu: không có.
- Nội dung: tài liệu đề xuất đặt khu tài khoản (tên, email/Đăng nhập, Đăng xuất) ở chân sidebar sáng và bỏ
  header "Sẵn sàng hỗ trợ" (D-08, §8). Nếu task landing-user-auth đặt khu tài khoản ở header chat, giai đoạn 1
  của đề xuất sẽ dời lại.
- Hành động mong muốn: không bắt buộc; tham khảo khi làm phần header/sidebar để tránh làm hai lần.

## Bàn giao

### HANDOFF-claude-agent-001 — S-01 … S-03

- Đã làm: tài liệu nghiên cứu + đề xuất, mockup, ảnh chụp.
- File: xem phạm vi trong `task.md`.
- Kiểm tra: `verification.md` V-01 … V-05.
- Chưa xong: người dùng trả lời §9; lập task triển khai cho từng giai đoạn.
- Người nhận: người dùng.

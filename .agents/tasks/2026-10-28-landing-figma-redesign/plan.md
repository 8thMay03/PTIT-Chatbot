# Plan: 2026-10-28-landing-figma-redesign

Nhánh `feat/landing-figma-redesign` tách từ `feat/landing-user-auth` tại `053b561`. Một agent (`claude-agent`) làm
tuần tự; reviewer `self_review`.

## Ánh xạ thiết kế → nội dung PTIT

| Khối Figma (node) | Bản dựng |
|---|---|
| Nav `2002:572` | Logo ô xám + "PTIT Chatbot" serif + "Trợ lý học vụ"; link Tính năng / Cách hoạt động / Câu hỏi thường gặp; nút giao diện; Đăng nhập + nút tối "Đăng ký" (đã đăng nhập: tên + "Vào trò chuyện") |
| Hero `2002:614` | Tiêu đề 2 dòng (dòng 2 màu xám), mô tả, nút tối "Bắt đầu trò chuyện" |
| Thẻ nghiêng `2002:535` | Thẻ "Câu hỏi gợi ý" và thẻ "Nguồn trích dẫn" (trang trí, ẩn với trình đọc màn hình, ẩn dưới 1100 px) |
| Khung soạn `2002:475` + nền chữ `2002:474` | Form thật: chip chủ đề, câu gợi ý, ô nhập, nút gửi → `/chat?q=`; nền chữ tiếng Việt mờ dần |
| Dải logo `2002:633` | Dải chủ đề hỗ trợ (không dùng logo bên thứ ba) |
| Bento `2002:663` | 5 thẻ: hỏi đáp tiếng Việt (minh hoạ hội thoại + nguồn), đúng phạm vi học vụ (nhãn nghiêng), trích dẫn điều/khoản, hiểu ngữ cảnh, lịch sử theo tài khoản |
| Carousel `2002:939` | "Cách hoạt động" 4 bước (thay lời chứng thực) |
| FAQ `2002:992` | 6 câu hỏi thật (gồm giới hạn, dữ liệu) |
| CTA `2002:1033` | Dải kêu gọi + nút tối |
| Footer `2002:1053` | Footer tối: logo, 3 cột link thật, dòng cuối |

## Nhiệm vụ

### S-01 — Token, font, CSS landing
- Agent: `claude-agent`; Trạng thái: `done`.
- File: `frontend/src/styles/tokens.css` (token `--lp-*` sáng/tối), `frontend/src/styles/landing.css`,
  `frontend/package.json` (+ `@fontsource/readex-pro`, `@fontsource/playfair-display`).

### S-02 — Component landing
- Agent: `claude-agent`; Trạng thái: `done`. Phụ thuộc S-01.
- File: `frontend/src/landing/*`.

### S-03 — `/chat?q=` điền sẵn câu hỏi; trang tài khoản cùng phong cách
- Agent: `claude-agent`; Trạng thái: `done`.
- File: `frontend/src/App.jsx`, `frontend/src/ChatView.jsx`, `frontend/src/lib/appRoute.js`,
  `frontend/src/styles/auth.css`, `frontend/src/auth/AuthLayout.jsx`.

### S-04 — Test, kiểm chứng, ảnh chụp
- Agent: `claude-agent`; Trạng thái: `done`. Phụ thuộc S-01 … S-03.
- File: test trong `frontend/src/landing/`, `frontend/src/App.test.jsx`, `frontend/src/lib/appRoute.test.js`.

## Kiểm chứng và review

- Verifier `claude-agent`: `npm test`, `npm run build`, `npm run check:bundle`; Playwright 360/768/1280 sáng/tối;
  so ảnh chụp 1440 px với ảnh Figma.
- Reviewer `claude-agent` (`self_review`).

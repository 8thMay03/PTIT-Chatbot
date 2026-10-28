# Review: 2026-10-28-landing-figma-redesign

- Reviewer: `claude-agent`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: diff `053b561..feat/landing-figma-redesign` (commit sau bàn giao).
- Cập nhật lúc: `2026-10-28T09:56:40+07:00`.

## Phạm vi và cơ sở đánh giá

- Đã đọc toàn bộ diff `frontend/src/landing/*`, `styles/landing.css`, `styles/tokens.css`, `styles/auth.css`,
  `App.jsx`, `ChatView.jsx`, `lib/appRoute.js`, test; đối chiếu V-01 … V-05 và ảnh Figma.

## Nhận xét

### R-01 — Font tiêu đề khác thiết kế

- Mức độ: `low`; bắt buộc: không; trạng thái: `deferred`.
- "PP Editorial New" là font thương mại (Pangram Pangram), không có bản quyền web và thiếu dấu tiếng Việt;
  Playfair Display rộng hơn nên tiêu đề tiếng Việt dài hơn bản Figma. Nếu dự án mua bản quyền một serif hẹp có
  tiếng Việt thì chỉ cần đổi `--lp-font-serif` trong `landing.css`.

### R-02 — Asset trang trí dựng lại bằng CSS

- Mức độ: `low`; bắt buộc: không; trạng thái: `deferred`.
- Phiên không tải được asset của Figma (403). Icon dùng lucide; vệt mờ nền, chữ gradient, quầng sáng là bản
  CSS gần đúng; logo đối tác, ảnh người, micro không dùng vì không trung thực với sản phẩm.

### R-03 — Landing không còn dùng màu maroon nhận diện

- Mức độ: `low`; bắt buộc: không; trạng thái: `resolved`.
- Theo thiết kế Figma (trung tính, nút tối), khác D-09 của task trước (giữ maroon làm màu nhận diện).
- Phản hồi/cách sửa (`2026-10-28T09:56:40+07:00`): người dùng yêu cầu nút màu đỏ hợp màu chủ đạo PTIT
  (`MSG-user-001`). `--lp-btn-bg`/`--lp-btn-bg-hover`/`--lp-btn-text`/`--lp-accent`/`--lp-accent-ring` trong
  `tokens.css` chuyển sang `--brand-*` (sáng: `#7D1F2C → #B8394B`, tối: `#972635 → #C53D52`, chữ trắng; tương phản
  chữ trắng ≥ 5.04:1). Áp cho nút chính (nav, hero, dải kêu gọi), nút "Bước tiếp theo", nút gửi, chấm carousel đang
  chọn, vòng focus, nút trang đăng nhập/đăng ký.
- Xác nhận của reviewer: đã xem ảnh chụp 1440 sáng/tối, 360, `/login` 1280 sáng/360 tối; test và
  `check:bundle` chạy lại đạt.

### Điểm đã kiểm và không có nhận xét

- `?q=` chỉ điền sẵn, không tự gửi; giá trị qua React (không chèn HTML); cắt 1000 ký tự; xoá khỏi URL.
- Màu thô chỉ nằm trong `tokens.css` (trừ `#000` làm kênh alpha của `mask-image`, có chú thích).
- Landing không kéo module chat/admin (check:bundle); font nạp ở chunk landing/auth.
- Nội dung không có số liệu, logo, lời chứng thực bịa; FAQ nói rõ quản trị viên có thể xem hội thoại (đúng với
  `/api/admin/conversations`).

## Lịch sử các vòng review

- `2026-10-28T09:25:00+07:00` — `claude-agent` (`self_review`) — `approved`; R-01 … R-03 `low`, `deferred`.
- `2026-10-28T09:56:40+07:00` — `claude-agent` (`self_review`) — `approved`; R-03 `resolved` (nút maroon).

## Kết luận

- Kết luận: `approved` (`self_review`).
- Nhận xét bắt buộc còn mở: không.
- Nhận xét hoãn lại: R-01, R-02. R-03 đã xử lý.

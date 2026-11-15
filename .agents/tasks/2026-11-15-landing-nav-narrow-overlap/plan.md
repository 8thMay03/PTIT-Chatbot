# Plan: 2026-11-15-landing-nav-narrow-overlap

Nhánh: `feat/landing-nav-narrow-overlap`, tách từ `dev` tại `11b7ac4` (lúc soạn task: `0fdd444`).

## Phân công

### S-01 — Cho tên thương hiệu co lại và rà các breakpoint của nav

- Agent: `claude-code`
- Trạng thái: `in_review`
- Mục tiêu: cho `.lp-nav-brand` và `.lp-brand-name` co được (`min-width: 0`, `overflow: hidden`, `text-overflow: ellipsis`) hoặc ẩn chữ thương hiệu ở bề rộng quá hẹp; kiểm tra lại các ngưỡng 480px và 640px để nút không đè lên nhau; phục vụ `AC-01`..`AC-04`.
- Phạm vi file được sửa: `frontend/src/styles/landing.css`; `frontend/src/landing/LandingPage.jsx` chỉ khi cần.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: diff, bộ ảnh chụp ở các bề rộng trong AC-01.
- Người nhận: `claude-code` (coordinator).

## Hợp đồng dùng chung

- Không áp dụng API.
- File mã nguồn dùng chung: `.lp-brand` dùng chung với `AuthLayout.jsx`; sửa quy tắc chung phải kiểm tra lại `/login`, `/register`.
- Lượt ghi năm file task: coordinator tổng hợp.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: `AC-01`..`AC-04`.
- Reviewer: `claude-code`; phạm vi: diff S-01.
- Hình thức review: `self_review` (một agent làm cả triển khai, kiểm chứng, review).
- Người xử lý nhận xét: agent S-01.

## Thứ tự tích hợp và kiểm chứng

1. S-01 triển khai.
2. Verifier kiểm tra bằng DevTools device mode trên Chrome hoặc Edge có giao diện (không dùng headless, vì headless không thu viewport dưới khoảng 500px); chạy test và build. Thực tế đã dùng viewport giả lập của Playwright (CDP), không bị giới hạn 500px (đã xác nhận `innerWidth = 320`); xem `verification.md`.
3. Review, sửa, kiểm tra lại; coordinator đóng task.

## Rủi ro và điều chỉnh kế hoạch

- Hiệu ứng `data-magnetic` và `data-pulse` trên nút có thể làm nút xê dịch khi rê chuột; kiểm tra không gây chồng lấn tạm thời.
- Bổ sung khi triển khai: trạng thái nav khi cuộn (`landing-motion.css`, `padding-inline: 12px` + viền) làm phần nội dung hẹp thêm 26px; các ngưỡng đã tính cả phần này.
- `data-magnetic` chỉ dùng `transform`, không đổi bố cục; chưa đo riêng độ lệch tạm thời khi rê chuột.

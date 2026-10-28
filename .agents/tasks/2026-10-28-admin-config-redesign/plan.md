# Plan: 2026-10-28-admin-config-redesign

## Phân công

### S-01 — Thiết kế lại ConfigView và CSS

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: bố cục mới theo AC-01…AC-05.
- Phạm vi file được sửa: `frontend/src/ConfigView.jsx`, `frontend/src/styles/config.css`,
  `frontend/src/styles/responsive.css`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: commit trên `feat/admin-config-redesign`.
- Người nhận: `claude-agent` (verifier).

### S-02 — Test hành vi chỉnh sửa

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: test hoàn tác từng trường, huỷ toàn bộ, khoá cài đặt phụ, kẹp số; phục vụ AC-02…AC-04, AC-06.
- Phạm vi file được sửa: `frontend/src/ConfigView.test.jsx` (mới).
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: test chạy được bằng `npm test`.
- Người nhận: `claude-agent`.

## Hợp đồng dùng chung

- API `/config` (GET/PUT) và `/config/reset`: không đổi payload.
- Cache `queryKeys.config` dùng chung với `ModelsView`; giữ `mergeConfigDraft`.
- Lớp CSS dùng chung với tab Mô hình được giữ: `.config-page-wrapper`, `.settings-subtabs-header`,
  `.config-header-*`, `.config-main-title`, `.config-main-desc`, `.btn-outline-reset`, `.btn-primary-save`.
- Lượt ghi năm file task: `claude-agent` (một agent).

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: AC-01…AC-06.
- Reviewer: `claude-agent`; phạm vi: toàn bộ diff của S-01, S-02.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-agent`.

## Thứ tự tích hợp và kiểm chứng

1. S-01, sau đó S-02.
2. Chạy test, build, `check:bundle`; chụp màn hình bằng Playwright với API giả lập.
3. Self-review, ghi `review.md`.
4. Người dùng xem giao diện; merge vào `dev` khi được đồng ý.

## Rủi ro và điều chỉnh kế hoạch

- Đổi tên/bỏ lớp CSS có thể ảnh hưởng tab Mô hình: đã grep các lớp cũ, chỉ bỏ lớp không còn JSX nào dùng.

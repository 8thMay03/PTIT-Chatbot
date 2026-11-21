# Review: 2026-11-21-models-settings-redesign

- Reviewer: `claude-agent`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: working tree trên `feat/models-settings-redesign` (nền `2948dc0`): 10 file sửa, 4 file mới trong
  `frontend/src`, mockup `docs/design/mockups/settings-models.html`.
- Cập nhật lúc: `2026-11-21T21:18:07+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 … AC-06; S-01 … S-03.
- File/thay đổi cần đọc: toàn bộ diff `frontend/src` của task.
- Bằng chứng kiểm chứng: `verification.md` V-01 … V-06.
- Điểm cần đánh giá: đúng hành vi kho mô hình (activate/xoá/embedding), khả năng truy cập của ngăn kéo, không mất dữ liệu
  form, hợp đồng route `#settings/models-*`, CSS sáng/tối, phạm vi file.

## Nhận xét

### R-01 — Ngăn kéo của panel bị ẩn khi đổi loại

- Vị trí: `frontend/src/models/ModelKindPanel.jsx` (`ProfileEditor hidden={!active}`).
- Vấn đề: ba panel luôn mounted. Nếu đang mở ngăn kéo mà route đổi loại (nút Back của trình duyệt), ngăn kéo của panel
  cũ có thể vẫn phủ trên trang.
- Tác động: người dùng thấy form của loại khác.
- Mức độ: `medium`; bắt buộc sửa: có.
- Người xử lý: claude-agent.
- Phản hồi: đã xử lý ngay trong S-01: truyền `active` xuống panel. Ngăn kéo ẩn (`hidden` trên scrim và panel, gỡ phím tắt) khi loại không còn
  được xem và giữ bản nháp để quay lại tiếp tục.
- Trạng thái: `resolved`.

### R-02 — Esc khi Modal mở trên ngăn kéo

- Vị trí: `frontend/src/models/ProfileDialog.jsx` (vòng 1: `ProfileDrawer.jsx`).
- Vấn đề: ngăn kéo và Modal cùng nghe `keydown` ở capture.
- Tác động: Esc có thể đóng cả hai.
- Mức độ: `low`; bắt buộc sửa: không.
- Người xử lý: claude-agent.
- Phản hồi: ngăn kéo bỏ qua Esc khi có `.modal-backdrop`. Hiện không có Modal nào mở từ trong ngăn kéo; đây là phòng xa.
- Trạng thái: `resolved`.

### R-03 — Không hỏi lại khi "Dùng" LLM/reranker

- Vị trí: `ModelKindPanel.requestActivate`.
- Vấn đề: một lần bấm đổi mô hình đang chạy cho mọi người dùng chat.
- Tác động: bấm nhầm thì đổi ngay. Hành vi này giống nút "Dùng mô hình này" cũ và có toast báo kết quả, đổi lại được
  bằng một lần bấm.
- Mức độ: `low`; bắt buộc sửa: không.
- Người xử lý: claude-agent.
- Phản hồi: giữ như mockup đã duyệt; ghi trong bàn giao.
- Trạng thái: `deferred` (theo dõi nếu người dùng muốn thêm xác nhận).

Ngoài các mục trên, không có nhận xét khác. Phạm vi đã đọc: toàn bộ diff `frontend/src` và năm file task.

## Kết luận

- Vòng 1: `approved` (self_review) trên working tree ngày `2026-11-21T21:08:24+07:00`.
- Vòng 2 (sau S-04): đã đọc diff `ProfileDialog.jsx`, CSS hộp thoại và test; đối chiếu V-07. Hành vi focus/Esc/scrim
  không đổi; thêm khoá cuộn nền và trả lại giá trị cũ khi đóng. Không có nhận xét mới. `approved` (self_review) ngày
  `2026-11-21T21:18:07+07:00`; không còn nhận xét bắt buộc chưa xử lý.

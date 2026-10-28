# Implementation: 2026-10-28-admin-config-redesign

## Tổng quan triển khai

Nhánh `feat/admin-config-redesign` (tách từ `dev` tại `04e3120`). S-01 và S-02 đã xong.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-10-28T23:47:00+07:00`.
- Đã làm:
  - Sắp lại bốn nhóm theo pipeline RAG ("Bước 1…4"): Truy xuất & tìm kiếm → Tái xếp hạng → Ngưỡng & kiểm
    soát an toàn → Mô hình sinh câu trả lời. Bố cục một cột (tối đa 1120px) thay cho hai cột lệch.
  - Mục lục bên trái (sticky) với tóm tắt giá trị từng nhóm và chấm báo nhóm có thay đổi; bấm để cuộn tới
    nhóm, `IntersectionObserver` đánh dấu nhóm đang xem. Màn ≤1100px: mục lục thành hàng chip cuộn ngang dính
    trên đầu vùng cuộn.
  - Thành phần nội bộ `SettingRow` (nhãn + giải thích | điều khiển), `SliderControl` (thanh trượt tô phần
    đã chọn, nhãn min/max, ô số có đơn vị), `NumberBox` (cho gõ tự do, chỉ nhận giá trị hợp lệ, kẹp khi
    blur/Enter), `Switch` (công tắc to hơn), nút chọn nhanh dạng segmented cho số lần thử lại.
  - Đánh dấu "Đã sửa" từng trường kèm nút hoàn tác về giá trị đã lưu; số thay đổi trên mỗi nhóm.
  - Thanh lưu cố định ở đáy: trạng thái đã lưu / "N thay đổi chưa lưu" + danh sách trường, nút
    "Huỷ thay đổi" và "Lưu cấu hình"; Ctrl/Cmd+S lưu khi tab đang hiển thị (bỏ qua khi panel bị `hidden`).
  - Cài đặt phụ (số truy vấn phụ, viết lại bằng LLM, hệ số ứng viên) luôn hiển thị, thụt vào và bị khoá khi
    công tắc cha tắt, có câu hướng dẫn bật công tắc.
  - Thanh tỷ trọng lai: một thanh trượt hai màu Vector/BM25 với chú thích phần trăm, thay cho thanh màu lớn
    và thanh trượt tách rời.
  - Đầu trang gọn: tiêu đề "Cấu hình RAG", mô tả luồng, nút "Khôi phục mặc định" (vẫn hỏi xác nhận).
  - CSS: bỏ các lớp cũ không còn dùng (`config-two-col-grid`, `config-panel-card`, `config-card-*`,
    `config-field-*`, `slider-with-number`, `custom-range-slider`, `number-input-box`, `pill-sel-*`,
    `hybrid-*`, `config-toggle-*`, `sub-setting*`, `settings-header-actions`) trong `config.css` và
    `responsive.css`; thêm lớp `cfg-*`.
- File thay đổi: `frontend/src/ConfigView.jsx`, `frontend/src/styles/config.css`,
  `frontend/src/styles/responsive.css`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: giữ nguyên payload API, `mergeConfigDraft`, `id`/`aria-label`
  cũ và lớp CSS dùng chung với tab Mô hình.
- Kiểm tra đã chạy: xem `verification.md` V-01…V-06.
- Còn lại/blocker: không có.

### S-02 — claude-agent

- Cập nhật lúc: `2026-10-28T23:47:00+07:00`.
- Đã làm: thêm `frontend/src/ConfigView.test.jsx` (3 test): hoàn tác riêng trường, huỷ toàn bộ không gọi
  PUT, khoá cài đặt phụ và kẹp số khi rời ô.
- Kiểm tra đã chạy: `npm test` — 16 file, 87 test đạt.
- Còn lại/blocker: không có.

## Bàn giao

### HANDOFF-claude-agent-001 — S-01, S-02

- Từ / đến: `claude-agent` / người dùng.
- Đã hoàn tất: giao diện mới tab Cấu hình RAG và test.
- File/branch/commit/patch: nhánh `feat/admin-config-redesign`.
- Kiểm chứng: V-01…V-06 `passed`.
- Review: `self_review`, `approved`, không có nhận xét bắt buộc.
- Hạn chế / còn lại: chưa thử trên Safari/Firefox thật (chỉ Chromium); chưa chạy với backend thật.
- Bước tiếp theo: người dùng xem giao diện, quyết định merge vào `dev`.

# Implementation: 2026-11-21-models-settings-redesign

## Tổng quan triển khai

S-01, S-02 và S-03 đã xong trên nhánh `feat/models-settings-redesign` (tách từ `dev` tại `2948dc0`). Đã commit trên nhánh
này và mở PR vào `dev` theo yêu cầu người dùng.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-11-21T21:08:24+07:00`.
- Đã làm:
  - Mới `models/activeModels.js`: `activeModelSummary(kind, registry, config)` trả tên, nhà cung cấp/mô hình và trạng
    thái của mô hình đang dùng. Hàm này dùng chung cho thẻ khâu và danh sách mobile. `normalizeEnvLlmProvider` chuyển
    từ `ModelKindPanel` sang đây.
  - Mới `models/ModelKindCards.jsx`: ba thẻ khâu là link `#settings/models-*`, có `data-settings-nav` và
    `aria-current="page"`. Ctrl/Cmd/Shift-click mở tab mới (dùng `navClick` từ `SettingsNav`). Chip trạng thái nằm cạnh
    tên mô hình, tên dài thì cắt.
  - `ModelKindPanel.jsx` viết lại phần giao diện:
    - Bỏ `ActiveModelCard` (ô select + "Dùng mô hình này") và `ProfileList`. Mỗi loại chỉ còn một card danh sách: hàng
      `.env` (reranker: Heuristic) rồi các mô hình trong kho.
    - Hàng đang dùng có dấu chọn và `aria-current`; các hàng khác có nút "Dùng" (`aria-label="Dùng <tên>"`). Cảnh báo
      của từng loại (thiếu API key, reranker tắt, lỗi nạp embedding, cần khởi động lại) nằm đầu card.
    - Embedding: "Dùng" mở Modal xác nhận trước khi gọi `activate`. Mô hình khác `VECTOR_DIM` bị khoá nút "Dùng".
  - Mới `models/ProfileDrawer.jsx` (S-04 đổi thành `ProfileDialog.jsx`): ngăn kéo phải, portal vào `body`, `role="dialog"`. Có Tab trap và trả focus khi
    đóng. Esc/scrim chỉ đóng khi form chưa đổi và không đang lưu/kiểm tra; khi Modal đang mở thì nhường Esc cho Modal.
  - Form thêm/sửa (`ProfileEditor`) giữ nguyên logic, chuyển từ `Section` sang ngăn kéo. Mô tả ngăn kéo nói rõ khi nào
    thay đổi có hiệu lực.
  - `ModelsView.jsx` hiện thẻ khâu ở đầu trang và nhận prop `onKindSelect`. Banner thông tin xanh đổi thành dòng chú
    thích cuối trang; cảnh báo `CONFIG_ENCRYPTION_KEY` giữ nguyên.
  - `fields.jsx`: bỏ `Section` (không còn dùng), export `KIND_ICONS`.
  - `models.css`: bỏ CSS hai cột, tab con, select và card hồ sơ cũ. Thêm CSS cho thẻ khâu (cùng token với bước
    pipeline), hàng danh sách, ngăn kéo (provider lưới 2 cột) và các khổ hẹp (1023/900/560px).
- File thay đổi: `frontend/src/ModelsView.jsx`, `frontend/src/models/ModelKindPanel.jsx`, `frontend/src/models/fields.jsx`,
  `frontend/src/models/ModelKindCards.jsx`, `frontend/src/models/ProfileDrawer.jsx` (nay `ProfileDialog.jsx`), `frontend/src/models/activeModels.js`,
  `frontend/src/styles/models.css`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: `ModelsView({ kind, onKindSelect })` như hợp đồng trong `plan.md`.
- Kiểm tra đã chạy: `verification.md` V-01 … V-04.
- Còn lại/blocker: không có.

### S-02 — claude-agent

- Cập nhật lúc: `2026-11-21T21:08:24+07:00`.
- Đã làm:
  - `SettingsView.jsx`: bỏ `settings-subbar`/`ModelKindNav`, truyền `onKindSelect={handleSelect}` cho `ModelsView`.
    Mô tả nhóm Mô hình đổi theo hành vi mới.
  - `SettingsView` đọc kho mô hình và cấu hình, dùng chung cache với `ModelsView`/`ConfigView`. Danh sách mục mobile
    hiện tên mô hình đang dùng, kèm trạng thái khi có cảnh báo.
  - `SettingsNav.jsx`: bỏ `ModelKindNav`, export `navClick`.
  - `config.css`: bỏ CSS `settings-subbar`/`settings-kind-*`. Thẻ khâu ẩn dưới 1024px (trong `models.css`).
- File thay đổi: `frontend/src/SettingsView.jsx`, `frontend/src/settings/SettingsNav.jsx`, `frontend/src/styles/config.css`.
- Kiểm tra đã chạy: `verification.md` V-01, V-05.
- Còn lại/blocker: không có.

### S-03 — claude-agent

- Cập nhật lúc: `2026-11-21T21:08:24+07:00`.
- Đã làm:
  - Viết lại test `ModelsView`: thẻ khâu, thêm qua ngăn kéo rồi bấm "Dùng", quay lại `.env`, hành vi Esc/scrim/Huỷ của
    ngăn kéo, xoá, embedding (khoá sai số chiều, huỷ/xác nhận).
  - Thêm `activeModels.test.js`.
  - `SettingsView.test.jsx`: đổi selector sang `.mdl-kind`, thêm test danh sách mobile có tên mô hình.
  - `SettingsNav.test.jsx`: bỏ test `ModelKindNav`.
  - Chạy test, build và chụp ảnh Playwright.
- File thay đổi: `frontend/src/models/ModelsView.test.jsx`, `frontend/src/models/activeModels.test.js`,
  `frontend/src/SettingsView.test.jsx`, `frontend/src/settings/SettingsNav.test.jsx`.
- Kiểm tra đã chạy: `verification.md`.
- Còn lại/blocker: không có.

## Trao đổi giữa agents

Không có (một agent làm tuần tự).

## Bàn giao

### HANDOFF-claude-agent-001 — S-01…S-03

- Từ / đến: `claude-agent` / người dùng.
- Đã hoàn tất: phương án A cho tab Mô hình.
- File/branch/commit/patch: nhánh `feat/models-settings-redesign`; commit `feat:` (mã + mockup) và `chore:` (task), PR vào `dev`.
- Kiểm chứng: `verification.md` (V-01 … V-06 đạt).
- Review: `review.md` — `approved` (self_review).
- Hạn chế / còn lại:
  - Ngăn kéo không khoá cuộn nền; vùng nội dung Cài đặt tự cuộn riêng nên không thấy trôi trong ảnh chụp.
  - Bấm "Dùng" với LLM/reranker áp dụng ngay, không hỏi lại (giống nút "Dùng mô hình này" cũ).
- Bước tiếp theo: người dùng review và merge PR.
- Phản hồi nhận bàn giao: chờ người dùng.

### S-04 — claude-agent

- Cập nhật lúc: `2026-11-21T21:18:07+07:00`.
- Đã làm:
  - Theo yêu cầu người dùng, đổi tên `ProfileDrawer.jsx` thành `ProfileDialog.jsx` và class `mdl-drawer*` thành
    `mdl-dialog*`.
  - Hộp thoại căn giữa bằng `position: fixed; inset: 0; margin: auto; height: fit-content`. Rộng `min(640px, 100% - 32px)`,
    cao tối đa `100dvh - 48px`; thân tự cuộn, header/footer cố định. Hiệu ứng vào là fade + scale nhẹ, tắt khi
    `prefers-reduced-motion`.
  - Thêm khoá cuộn nền (`body.style.overflow`) như `Modal`.
  - Hành vi focus/Tab/Esc/scrim giữ nguyên. Áp dụng cho cả Thêm và Sửa vì dùng chung thành phần.
- File thay đổi: `frontend/src/models/ProfileDialog.jsx`, `frontend/src/models/ModelKindPanel.jsx`,
  `frontend/src/styles/models.css`, `frontend/src/models/ModelsView.test.jsx` (selector, tên test).
- Kiểm tra đã chạy: `verification.md` V-07.
- Còn lại/blocker: không có.

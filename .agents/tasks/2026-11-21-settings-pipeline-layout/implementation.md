# Implementation: 2026-11-21-settings-pipeline-layout

## Tổng quan triển khai

S-01, S-02 và S-03 đã xong trên nhánh `feat/settings-pipeline-layout` (tách từ `dev` tại `43e48f8`). Chưa commit;
toàn bộ thay đổi nằm trong working tree.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-11-21T17:34:14+07:00`.
- Đã làm:
  - `SettingsView` dựng lại thành header ("Cài đặt", mô tả theo nhóm, "Lần lưu gần nhất", nút "Thử với câu hỏi")
    và ba tab nhóm; bỏ cột danh mục dọc.
  - Tab "Hệ thống trả lời" truyền `PipelineSteps` vào `ConfigView` qua prop `lead`, để dải bước cuộn cùng form còn
    header/tab cố định.
  - Tab "Mô hình" có `ModelKindNav` (Ngôn ngữ / Nhúng / Xếp hạng). Tab "Giao diện" đặt `ThemePicker` trong card có
    header.
  - `SettingsNav.jsx`: bỏ `SettingsSidebar`. Thêm `SettingsTabs`, `ModelKindNav`, `settingsGroupOf`, `DirtyDot`
    (export). `SettingsIndex` (mobile) nhận `summaries` để hiện giá trị đang dùng thay cho dòng gợi ý.
  - Link điều hướng giữ `href`; Ctrl/Cmd/Shift/nút giữa thì để trình duyệt mở tab mới.
  - Mới `PipelineSteps.jsx`: bốn bước có số thứ tự, icon, chip giá trị, chấm "chưa lưu", `aria-current="step"`, hai
    đầu "Câu hỏi"/"Câu trả lời" (ẩn dưới 1280px).
  - Mới `pipelineSummary.js`: nhãn chip từ bản nháp. Ngưỡng cosine/rerank lấy ghi đè hoặc giá trị hiệu chỉnh; thiếu
    cả hai thì ghi "bỏ qua". `shortModelName`, `RERANKER_PROVIDER_LABELS` chuyển từ `ConfigView` sang đây.
  - "Thử với câu hỏi" là ngăn kéo cố định bên phải ở mọi khổ (trước đây là cột ở ≥1280px), có scrim và hiệu ứng
    trượt (tắt khi `prefers-reduced-motion`). Logic focus/Esc của `RetrievalTestPanel` giữ nguyên, chỉ sửa comment.
  - `models.css`: banner kho mô hình đổi sang tông trung tính; bo góc `.mdl-card` dùng `--radius` như card form.
  - `tokens.css`: thêm `--on-solid-soft` và `--shadow-brand` cho bước đang chọn, để màu thô vẫn chỉ nằm trong tokens.
- File thay đổi: `frontend/src/SettingsView.jsx`, `frontend/src/settings/SettingsNav.jsx`,
  `frontend/src/settings/PipelineSteps.jsx`, `frontend/src/settings/pipelineSummary.js`,
  `frontend/src/settings/RetrievalTestPanel.jsx`, `frontend/src/styles/config.css`, `frontend/src/styles/models.css`,
  `frontend/src/styles/tokens.css`; mockup `docs/design/mockups/settings-pipeline.html`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: props của `SettingsView` không đổi nên `AdminShell` không phải sửa.
- Kiểm tra đã chạy: xem `verification.md` V-01 … V-08.
- Còn lại/blocker: không có.

### S-02 — claude-agent

- Cập nhật lúc: `2026-11-21T17:34:14+07:00`.
- Đã làm:
  - `ConfigView` nhận `{ activeSection, lead, onDraftState }`.
  - Mỗi `<section>` có `hidden={activeSection !== key}`: vẫn mounted nên bản nháp, thanh lưu và các test tương tác
    trường của nhiều bước giữ nguyên.
  - Bỏ scroll-spy và `scrollIntoView`; đổi bước thì đưa vùng cuộn về đầu.
  - Tiêu đề và mô tả mục nằm trong `<header className="config-section-head">`. Câu trong callout ngưỡng đổi từ
    "bảng … bên phải" thành "nút … ở đầu trang".
  - CSS: mỗi section là một card (container query). Từ 640px, `.config-field-group` thành lưới nhãn–hint trái /
    điều khiển phải (`grid-auto-flow: dense`). Trường công tắc trải hết hàng; `legend` của fieldset được `float` để
    thành grid item. Tham số phụ (`.sub-setting-row`) cùng lưới. Khung xám của `bordered-group` được bỏ.
  - Xoá `settings/scrollSpy.js` và test của nó vì không còn dùng.
- File thay đổi: `frontend/src/ConfigView.jsx`, `frontend/src/styles/config.css`, xoá `frontend/src/settings/scrollSpy.js`,
  `frontend/src/settings/scrollSpy.test.js`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: không có.
- Kiểm tra đã chạy: `verification.md` V-02, V-03, V-04.
- Còn lại/blocker: không có.

### S-03 — claude-agent

- Cập nhật lúc: `2026-11-21T17:34:14+07:00`.
- Đã làm:
  - Viết lại test `SettingsNav` (tab, thanh loại mô hình, dải bước, danh sách mobile có giá trị, Ctrl+click).
  - Viết lại 4 test cũ của `SettingsView` dựa trên cột danh mục/scroll, thêm test dải bước và test giữ bản nháp khi
    đổi bước.
  - Thay test cuộn anchor trong `AdminApp.test.jsx` bằng test đổi bước/lịch sử.
  - Thêm `pipelineSummary.test.js`.
  - Chạy test/build và chụp ảnh Playwright.
- File thay đổi: `frontend/src/settings/SettingsNav.test.jsx`, `frontend/src/SettingsView.test.jsx`,
  `frontend/src/admin/AdminApp.test.jsx`, `frontend/src/settings/pipelineSummary.test.js`, `verification.md`.
- Kiểm tra đã chạy: `verification.md`.
- Còn lại/blocker: không có.

## Trao đổi giữa agents

Không có (một agent làm tuần tự).

## Bàn giao

### HANDOFF-claude-agent-001 — S-01…S-03

- Từ / đến: `claude-agent` / người dùng.
- Đã hoàn tất: bố cục phương án A cho màn Cài đặt quản trị.
- File/branch/commit/patch: nhánh `feat/settings-pipeline-layout`, chưa commit.
- Kiểm chứng: `verification.md` (V-01 … V-08 đạt).
- Review: `review.md` — `approved` (self_review), không còn nhận xét bắt buộc.
- Hạn chế / còn lại:
  - Nút "Về mặc định" theo bước (có trong mockup) nằm ngoài phạm vi.
  - Form bên trong `ModelKindPanel` chỉ được chỉnh tông, chưa chuyển sang kiểu hàng nhãn–điều khiển.
- Bước tiếp theo: người dùng xem lại; commit và mở PR vào `dev` khi người dùng đồng ý.
- Phản hồi nhận bàn giao: chờ người dùng.

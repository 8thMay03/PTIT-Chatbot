# Plan: 2026-11-21-settings-pipeline-layout

## Phân công

### S-01 — Khung trang: header, tab, dải bước, thanh loại mô hình

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-01`, `AC-02`, `AC-05`, `AC-06`, `AC-07`.
- Phạm vi file được sửa: `frontend/src/SettingsView.jsx`, `frontend/src/settings/SettingsNav.jsx`, mới
  `frontend/src/settings/PipelineSteps.jsx`, mới `frontend/src/settings/pipelineSummary.js` (+ test),
  `frontend/src/styles/config.css`, `frontend/src/styles/models.css` (banner chỉnh bằng CSS, không sửa
  `ModelsView.jsx`), `frontend/src/styles/tokens.css`.
- Phụ thuộc: không.
- Đầu ra/bàn giao: `SettingsView` truyền `activeSection` cho `ConfigView`; tóm tắt bước lấy từ `onDraftState`.
- Người nhận: `claude-agent` (S-02).

### S-02 — Form "Hệ thống trả lời" theo từng bước

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-03`, `AC-04`.
- Phạm vi file được sửa: `frontend/src/ConfigView.jsx`, `frontend/src/styles/config.css`, xoá
  `frontend/src/settings/scrollSpy.js` + `scrollSpy.test.js`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: section không thuộc bước đang chọn có `hidden` (vẫn mounted); bỏ scroll-spy, `scrollRequest`,
  `onSectionActive`.
- Người nhận: `claude-agent` (S-03).

### S-03 — Test, kiểm chứng và ảnh chụp

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-08` và bằng chứng cho `AC-01` … `AC-07`.
- Phạm vi file được sửa: test liên quan, `verification.md`.
- Phụ thuộc: S-01, S-02.
- Đầu ra/bàn giao: kết quả `npm test`, `npm run build`, ảnh Playwright.
- Người nhận: reviewer.

## Hợp đồng dùng chung

- Route không đổi: `readAdminRoute`/`adminRouteHash`, `ADMIN_ANSWER_SECTIONS`, `ADMIN_MODEL_SECTIONS`.
- `SettingsView` props không đổi (`section`, `onSectionChange`, `onBackToList`, `theme`, `onThemeChange`), nên
  `AdminShell.jsx` không cần sửa.
- `ConfigView` props mới: `{ activeSection, onDraftState }` (bỏ `scrollRequest`, `onSectionActive`).
- `pipelineSummary(values, config, calibrated)` → `{ retrieval: string[], reranker: string[], gate: string[],
  generation: string[] }` (nhãn chip ngắn), dùng ở dải bước và danh sách mobile.
- Lượt ghi năm file task: một agent, ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: AC-01 … AC-08.
- Reviewer: `claude-agent`; phạm vi: toàn bộ diff nhánh.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-agent`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 rồi S-02 trên cùng nhánh `feat/settings-pipeline-layout`.
2. S-03 chạy test, build, chụp ảnh desktop sáng/tối và mobile.
3. Self-review ghi `review.md`; sửa nhận xét bắt buộc, chạy lại kiểm tra bị ảnh hưởng.
4. Coordinator đối chiếu AC, đóng task khi review `approved`.

## Rủi ro và điều chỉnh kế hoạch

- Ẩn section bằng `hidden` thay vì bỏ khỏi DOM để giữ bản nháp và test hiện có tương tác với mọi trường.
- Bố cục hàng nhãn – điều khiển làm bằng CSS grid trên `.config-field-group` (không đổi cấu trúc JSX từng trường)
  để giới hạn rủi ro; `legend` của fieldset cần `float` để thành grid item.

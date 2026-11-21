# Plan: 2026-11-21-models-settings-redesign

## Phân công

### S-01 — Thẻ khâu, danh sách chọn, ngăn kéo

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: dựng phương án A trong tab Mô hình; phục vụ `AC-01` … `AC-04`.
- Phạm vi file được sửa: `frontend/src/ModelsView.jsx`, `frontend/src/models/ModelKindPanel.jsx`,
  `frontend/src/models/fields.jsx`, mới `frontend/src/models/ModelKindCards.jsx`, `frontend/src/models/activeModels.js`,
  `frontend/src/models/ProfileDrawer.jsx`, `frontend/src/styles/models.css`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: mã trong working tree.
- Người nhận: `claude-agent` (S-02).

### S-02 — Nối vào SettingsView, mobile

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: bỏ `ModelKindNav`, truyền điều hướng cho thẻ khâu, tóm tắt mô hình trong danh sách mobile; phục vụ `AC-01`,
  `AC-05`.
- Phạm vi file được sửa: `frontend/src/SettingsView.jsx`, `frontend/src/settings/SettingsNav.jsx`,
  `frontend/src/styles/config.css`.
- Phụ thuộc: S-01 (`ModelsView` nhận `onKindSelect`, `activeModels.js`).
- Đầu ra/bàn giao: mã trong working tree.
- Người nhận: `claude-agent` (S-03).

### S-03 — Test, build, ảnh chụp

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: cập nhật test bị ảnh hưởng, thêm test mới; chạy `npm test`, `npm run build`; chụp ảnh; phục vụ `AC-06`.
- Phạm vi file được sửa: `frontend/src/models/ModelsView.test.jsx`, mới `frontend/src/models/activeModels.test.js`,
  `frontend/src/SettingsView.test.jsx`, `frontend/src/settings/SettingsNav.test.jsx`, `verification.md`.
- Phụ thuộc: S-01, S-02.
- Người nhận: người dùng.

## Hợp đồng dùng chung

- `ModelsView({ kind, onKindSelect })`: `onKindSelect(sectionKey)` nhận `models-llm` | `models-embedding` |
  `models-reranker`; thẻ khâu vẫn có `href` để mở tab mới.
- `activeModelSummary(kind, registry, config)` → `{ name, meta, status: { tone, label } }`, dùng cho thẻ khâu và danh
  sách mobile.
- API backend không đổi.
- Lượt ghi năm file task: claude-agent ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: AC-01 … AC-06.
- Reviewer: `claude-agent`; phạm vi: toàn bộ diff của task.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-agent`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 rồi S-02 (cùng agent, tuần tự).
2. S-03: test, build, ảnh chụp; ghi `verification.md`.
3. Self review trong `review.md`; sửa nhận xét bắt buộc, kiểm tra lại.
4. Đóng task khi AC đạt và review `approved`; commit/PR khi người dùng đồng ý.

## Rủi ro và điều chỉnh kế hoạch

- Ngăn kéo nằm trong vùng có `overflow: hidden`/animation: render qua portal vào `document.body` để `position: fixed`
  không bị cắt (xem ghi chú sidebar popover).
- Bấm "Dùng" có hiệu lực ngay: chỉ embedding cần xác nhận vì phải khởi động lại; LLM/reranker giữ hành vi áp dụng ngay
  như nút "Dùng mô hình này" cũ.

### S-04 — Hộp thoại giữa màn hình thay ngăn kéo

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: theo yêu cầu người dùng, form Thêm/Sửa hiện ở giữa màn hình; phục vụ `AC-04`.
- Phạm vi file được sửa: `frontend/src/models/ProfileDrawer.jsx` → `ProfileDialog.jsx`, `frontend/src/models/ModelKindPanel.jsx`,
  `frontend/src/styles/models.css`, `frontend/src/models/ModelsView.test.jsx`.
- Phụ thuộc: S-01 … S-03.
- Người nhận: người dùng.

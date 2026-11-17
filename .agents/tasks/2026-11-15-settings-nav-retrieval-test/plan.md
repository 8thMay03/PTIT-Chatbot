# Plan: 2026-11-15-settings-nav-retrieval-test

## Phân công

### S-01 — Route và khung danh mục dọc

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: hash `#settings/<key>` mới, ánh xạ hash cũ, cột danh mục (desktop) và danh sách → trang (mobile); phục vụ
  `AC-01`, `AC-02`.
- Phạm vi file được sửa: `frontend/src/lib/appRoute.js`, `frontend/src/lib/appRoute.test.js`,
  `frontend/src/admin/AdminShell.jsx`, `frontend/src/SettingsView.jsx`, mới `frontend/src/settings/SettingsNav.jsx`,
  `frontend/src/styles/config.css`, `frontend/src/styles/responsive.css`, `frontend/src/admin/AdminApp.test.jsx`.
- Phụ thuộc: task `2026-11-15-settings-gate-savebar` đã merge vào `dev`.
- Đầu ra/bàn giao: hợp đồng route (mục "Hợp đồng dùng chung"); `SettingsView` nhận `section` thay cho `tab`.
- Người nhận: `claude-agent` (S-02).
- Ghi chú: `ModelsView` hiện tự giữ tab con bằng localStorage `ptit_models_tab`; chuyển sang nhận `kind` từ route, dọn
  khoá cũ như cách đã dọn `ptit_added_providers`.

### S-02 — Form "Hệ thống trả lời" một cột theo pipeline

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-03`; anchor + scrollspy và chấm "có thay đổi" cho `AC-01`.
- Phạm vi file được sửa: `frontend/src/ConfigView.jsx`, `frontend/src/styles/config.css`,
  `frontend/src/models/ModelKindPanel.jsx` (link chéo), test `ConfigView.*.test.jsx`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: `ConfigView` xuất danh sách trường đã đổi theo mục (cho chấm ở danh mục) và giá trị nháp (cho S-03).
- Người nhận: `claude-agent` (S-03).
- Ghi chú: scrollspy dùng `IntersectionObserver`, có fallback khi môi trường test không có (jsdom).

### S-03 — Bảng "Thử với câu hỏi" và so ngưỡng nháp

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-04`, `AC-05`.
- Phạm vi file được sửa: mới `frontend/src/api/retrieval.js`, `frontend/src/api/index.js`,
  `frontend/src/api/queryClient.js` (nếu cần query key), mới `frontend/src/settings/RetrievalTestPanel.jsx`, mới
  `frontend/src/lib/gateDecision.js` + `gateDecision.test.js`, `frontend/src/SettingsView.jsx` (gắn bảng),
  `frontend/src/styles/config.css`, test component mới.
- Phụ thuộc: S-02 (giá trị nháp, bố cục cột).
- Đầu ra/bàn giao: bảng thử dùng `useMutation` hoặc `AbortController` để huỷ request cũ.
- Người nhận: `claude-agent` (S-05).
- Ghi chú: bộ ca của `gateDecision.test.js` chép từ `backend/tests/test_retrieval_confidence.py` (đạt/không đạt từng
  tín hiệu, thiếu tín hiệu, context rỗng, ngưỡng `null`); ghi đường dẫn test backend trong comment để người sửa luật
  biết phải sửa cả hai.

### S-04 — Backend `updated_at` cho `/config`

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-06` (phần backend + hiển thị header).
- Phạm vi file được sửa: `backend/app/api/schemas.py`, `backend/app/api/routes.py`, `backend/app/core/config_store.py`,
  migration mới trong `backend/alembic/versions/` nếu cần, `backend/tests/test_config_api.py`,
  `backend/tests/test_config_persistence.py`; frontend `frontend/src/SettingsView.jsx` hoặc header của form.
- Phụ thuộc: không (backend chạy song song S-01…S-03 được); phần hiển thị sau S-02.
- Đầu ra/bàn giao: trường `updated_at` trong `FullConfigResponse`.
- Người nhận: `claude-agent` (S-05).
- Ghi chú: `max(app_config_overrides.updated_at)` **không đủ**. Khi một trường trở về giá trị `.env`, `save_overrides`
  xoá dòng, nên lần lưu đó không để lại dấu thời gian; reset cũng xoá hết dòng. Cần một nguồn riêng, ví dụ một dòng
  metadata (key ngoài `PERSISTED_FIELDS`) ghi trong `settings_transaction`/`reset_stored_config`. Dòng metadata này
  phải bị bỏ qua khi nạp override lúc khởi động.

### S-05 — Kiểm chứng và ảnh chụp

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-07` và bằng chứng cho `AC-01` … `AC-06`.
- Phạm vi file được sửa: `verification.md`.
- Phụ thuộc: S-01 … S-04.
- Đầu ra/bàn giao: kết quả lệnh, ảnh.
- Người nhận: reviewer.

## Hợp đồng dùng chung

- **Route Settings admin** (S-01 cung cấp, S-02/S-03 dùng):
  - `readAdminRoute("#settings/<key>")` → `{ view: "settings", section: <key>, datasetId: null }`; key hợp lệ:
    `retrieval | reranker | gate | generation | models-llm | models-embedding | models-reranker | appearance`; key lạ hoặc
    `config` → `retrieval`; `models` → `models-llm`.
  - `adminRouteHash({ view: "settings", section })` → `settings/<section>`.
  - `legacyHashToAdmin` (app sinh viên) trả `/admin#settings/<key mới>`; `settings/appearance` vẫn trả `null`.
- **`GET`/`PUT`/`POST /config/reset` response** (S-04 cung cấp): thêm `updated_at: string | null` (ISO 8601). Client cũ
  bỏ qua được.
- **`POST /api/retrieval/test`** (có sẵn, không đổi): request `{ query, top_k?, dataset_ids? }`; response
  `{ query, contexts[], retrieval_debug{ rewritten_query, retrieval_queries, confidence{ reason, signals{vector,
  bm25_norm, rerank}, thresholds{ min_bm25_norm_score, min_vector_score, min_rerank_score, embedding_model,
  vector_source, rerank_source } }, … }, strong_context }` (`GateThresholds.as_dict()` trong `confidence.py`).
- File mã nguồn dùng chung: `ConfigView.jsx`, `SettingsView.jsx`, `config.css` — chỉ `claude-agent` sửa, tuần tự S-01 →
  S-02 → S-03.
- Lượt ghi năm file task: `claude-agent` ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: `AC-01` … `AC-07`.
- Reviewer: `claude-agent`; phạm vi: toàn bộ diff nhánh `feat/settings-nav-retrieval-test`.
- Hình thức review: `self_review` nếu chỉ một agent làm.
- Người xử lý nhận xét: `claude-agent`.

## Thứ tự tích hợp và kiểm chứng

1. Xác nhận task giai đoạn 1 đã merge; cập nhật `dev`; tách nhánh; ghi commit nền.
2. S-01 → S-02 → S-03 tuần tự; S-04 làm song song hoặc xen kẽ (file backend riêng).
3. S-05: toàn bộ lệnh kiểm tra + ảnh.
4. Review, sửa, kiểm tra lại; coordinator đóng task, mở PR vào `dev`.

## Rủi ro và điều chỉnh kế hoạch

- Luật gate ở frontend lệch backend (R-02 của task nghiên cứu) → bộ ca chung + comment chéo; nếu luật gate đổi thường
  xuyên, chuyển sang backend tính "bản nháp" (task sau).
- Scrollspy và drawer khó test trong jsdom → test logic chọn mục bằng hàm thuần; kiểm tra tương tác bằng Playwright thủ
  công, ghi trong verification.
- `POST /retrieval/test` chạy pipeline thật (embedding, có thể gọi LLM khi bật viết lại câu hỏi bằng LLM) → tốn chi phí;
  ghi chú trên bảng và không tự chạy khi gõ.
- Đổi `tab` → `section` trong route chạm nhiều test admin → cập nhật test trong cùng S-01.

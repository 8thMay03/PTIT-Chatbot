# Plan: 2026-11-15-settings-gate-savebar

## Phân công

### S-01 — Backend: xoá ghi đè ngưỡng bằng `null` tường minh

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: PUT `/config` nhận `guardrails.min_vector_score: null` / `min_rerank_score: null` là "xoá ghi đè"; phục vụ
  `AC-03`.
- Phạm vi file được sửa: `backend/app/core/config.py` (khối guardrails trong `update_runtime_config`, quanh dòng
  682-695), `backend/tests/test_config_api.py`, `backend/tests/test_config_persistence.py`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: hợp đồng ở mục "Hợp đồng dùng chung"; test xanh.
- Người nhận: `claude-agent` (S-02).
- Gợi ý: route đã dùng `model_dump(exclude_unset=True)` nên phân biệt được "không gửi" và "gửi `null`". Đặt settings về
  `_INITIAL_SETTINGS[field]` (giá trị `.env`); `save_overrides` sẽ tự xoá dòng vì giá trị bằng ban đầu.

### S-02 — Frontend: nhóm Ngưỡng tin cậy + chỉ gửi trường đã đổi

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: nhóm "Ngưỡng tin cậy" theo `AC-01`; payload PUT chỉ chứa trường đã đổi theo `AC-02`; link "Dùng giá trị hiệu
  chỉnh" theo `AC-03`.
- Phạm vi file được sửa: `frontend/src/ConfigView.jsx`, `frontend/src/lib/configDraft.js`,
  `frontend/src/lib/configDraft.test.js`, test mới `frontend/src/ConfigView.gate.test.jsx` (hoặc tên tương đương),
  `frontend/src/ConfigView.cache.test.jsx` nếu fixture cần thêm trường.
- Phụ thuộc: S-01 (hợp đồng `null`). Nếu S-01 chưa merge, ẩn link và để TODO — không áp dụng vì cùng task, làm tuần tự.
- Đầu ra/bàn giao: hàm thuần tính payload từ `values` và `savedSnapshot` (có test), UI nhóm ngưỡng mới.
- Người nhận: `claude-agent` (S-03).
- Ghi chú: `valuesFromConfig` phải giữ `null` cho `min_vector_score`/`min_rerank_score` thay vì rơi về số mặc định; ánh
  xạ `min_bm25_norm_score`. Điều kiện hiện ngưỡng reranker đọc `reranker.enabled` (bản nháp) và `reranker.provider` (từ
  cache `/config`).

### S-03 — Frontend: thanh lưu, đánh dấu trường đã sửa, vùng nguy hiểm

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-04`, `AC-05`.
- Phạm vi file được sửa: `frontend/src/ConfigView.jsx`, `frontend/src/styles/config.css`, có thể thêm
  `frontend/src/components/SaveBar.jsx`; test cho Hủy/trả từng trường/đếm thay đổi.
- Phụ thuộc: S-02 (cùng file `ConfigView.jsx`).
- Đầu ra/bàn giao: thanh lưu dùng lại được ở giai đoạn 2 (nhận danh sách thay đổi, `onDiscard`, `onSave`, `saving`).
- Người nhận: `claude-agent` (S-04).
- Ghi chú: thanh lưu cần `role="region"` + `aria-label`, không che trường cuối (thêm padding đáy vùng cuộn); trên mobile
  rộng toàn màn với nút đủ lớn để chạm.

### S-04 — Nhãn và thị giác

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-06`.
- Phạm vi file được sửa: `frontend/src/SettingsView.jsx`, `frontend/src/admin/AdminShell.jsx`,
  `frontend/src/models/catalog.js`, `frontend/src/styles/config.css`, `frontend/src/ConfigView.jsx` (phạm vi thanh hệ
  số, mô tả), test có chuỗi "Settings"/nhãn mô hình (`admin/AdminApp.test.jsx`, `models/ModelsView.test.jsx`,
  `App.test.jsx` nếu có).
- Phụ thuộc: S-03 (cùng `config.css`, `ConfigView.jsx`).
- Đầu ra/bàn giao: nhãn và màu theo AC-06.
- Người nhận: `claude-agent` (S-05).

### S-05 — Kiểm chứng và ảnh chụp

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-07` và bằng chứng cho `AC-01` … `AC-06`.
- Phạm vi file được sửa: `verification.md`; ảnh lưu ngoài repo hoặc trong `docs/design/assets/` nếu reviewer cần.
- Phụ thuộc: S-01 … S-04.
- Đầu ra/bàn giao: kết quả lệnh, ảnh trước/sau.
- Người nhận: reviewer.

## Hợp đồng dùng chung

- **PUT `/config` — `guardrails.min_vector_score` / `guardrails.min_rerank_score`** (S-01 cung cấp, S-02 dùng):
  - Không có khoá trong payload → giữ nguyên.
  - Có khoá, giá trị `null` → xoá ghi đè: settings về giá trị `.env` ban đầu; dòng tương ứng trong
    `app_config_overrides` bị xoá ở lần lưu; response phản ánh ngưỡng hiệu lực mới và `vector_threshold_source` là
    `calibrated` hoặc `uncalibrated`.
  - Có khoá, giá trị số → như hiện tại (bỏ qua 0.30 cũ và giá trị trùng ngưỡng hiệu lực).
  - ~~Không đổi schema response.~~ Cập nhật `2026-11-16` (D-1): `guardrails` trong response thêm 3 trường tuỳ chọn
    `calibrated_min_vector_score`, `rerank_threshold_source`, `calibrated_min_rerank_score`; trường cũ giữ nguyên.
- File mã nguồn dùng chung: `frontend/src/ConfigView.jsx`, `frontend/src/styles/config.css` — chỉ `claude-agent` sửa,
  tuần tự S-02 → S-03 → S-04.
- Lượt ghi năm file task: `claude-agent` ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: `AC-01` … `AC-07`.
- Reviewer: `claude-agent`; phạm vi: toàn bộ diff của nhánh `feat/settings-gate-savebar`.
- Hình thức review: `self_review` nếu chỉ một agent làm; ghi rõ khi có reviewer độc lập.
- Người xử lý nhận xét: `claude-agent`.

## Thứ tự tích hợp và kiểm chứng

1. Cập nhật `dev`, tách `feat/settings-gate-savebar`; ghi commit nền vào `implementation.md`.
2. S-01 → chạy `python -m pytest tests/test_config_api.py tests/test_config_persistence.py`.
3. S-02 → S-03 → S-04 tuần tự, chạy `npm test` sau mỗi bước.
4. S-05: `npm test`, `npm run build`, `python -m pytest`; chụp ảnh.
5. Review, sửa nhận xét, kiểm tra lại; coordinator đóng task khi đủ điều kiện, mở PR vào `dev`.

## Rủi ro và điều chỉnh kế hoạch

- Fixture `/config` trong test frontend có thể thiếu `min_bm25_norm_score`, `min_rerank_score`, `vector_threshold_source`
  → cập nhật fixture, giữ một ca thiếu trường để chắc UI không vỡ với backend cũ.
- Bỏ gửi `min_bm25_score` có thể làm test frontend cũ kiểm payload đầy đủ thất bại → sửa test theo AC-02, không giữ
  hành vi cũ.
- Đổi nhãn "Settings" có thể làm test tìm theo tên nút thất bại → cập nhật test.
- Hai quản trị viên cùng sửa: gửi trường đã đổi giảm việc ghi đè lẫn nhau nhưng không loại bỏ hoàn toàn; ngoài phạm vi.

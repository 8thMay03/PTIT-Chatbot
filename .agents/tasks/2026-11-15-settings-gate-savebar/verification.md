# Verification: 2026-11-15-settings-gate-savebar

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: `feat/settings-gate-savebar` tại `415afe3`.
- Môi trường: Windows 11, Node 24.14.0 (Vitest 3.2.7, Vite 5.4.21), Python của `backend/.venv` (pytest). Ảnh chụp bằng
  `playwright-core` + Chromium 1234 cài sẵn, API giả lập (`/api/**`), dev server Vite.
- Thời điểm: `2026-11-16T00:06:27+07:00`.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Lệnh: `npx vitest run src/ConfigView.gate.test.jsx` (`frontend/`).
- Ca: "không còn điều khiển BM25 thô…" (không có `#cfg-minbm25`; `#cfg-minbm25norm` min 0, max 1, step 0.01; mô tả
  chứa "đoạn khớp nhất", câu từ chối, "không gọi mô hình"); `calibrated` (huy hiệu "Đã hiệu chỉnh cho
  text-embedding-3-small", ô 0.37); `override` (huy hiệu "Ghi đè", link "Dùng giá trị hiệu chỉnh (0.37)");
  `uncalibrated` (cảnh báo "đang bỏ qua tín hiệu này", ô rỗng, không thanh trượt, không có "0.30"); reranker
  `heuristic` → không có ô rerank, dòng "không áp dụng với Heuristic"; `cross-encoder` bật → ô −1.65 + huy hiệu, tắt
  trong bản nháp → ẩn.
- Kết quả: 16/16 (sau bổ sung: 17/17) passed. Ảnh: `after-*-gate.png`.
- Trạng thái: `passed`.

### V-02 — AC-02

- Lệnh: `ConfigView.gate.test.jsx` nhóm "payload chỉ gồm trường đã đổi"; `src/lib/configDraft.test.js`
  `buildConfigPayload`.
- Kết quả: đổi Top-K khi đang ghi đè cosine → body đúng `{ retrieval: { top_k: 6 } }`; đổi cosine →
  `{ guardrails: { min_vector_score: 0.45 } }`; không payload nào chứa `min_bm25_score`; không đổi gì → `{}`.
- Trạng thái: `passed`.

### V-03 — AC-03

- Lệnh: `.venv/Scripts/python.exe -m pytest tests/test_config_api.py tests/test_config_persistence.py -q` (`backend/`).
- Kết quả: 34 passed. Ca mới: `test_null_vector_threshold_clears_override` (nguồn về `calibrated`, ngưỡng 0.37),
  `test_null_vector_threshold_on_uncalibrated_model_disables_signal`, `test_null_rerank_threshold_clears_override`,
  `test_omitted_thresholds_keep_overrides`, `test_null_threshold_removes_override_row_and_survives_restart` (dòng
  `retrieval_min_vector_score`/`retrieval_min_rerank_score` bị xoá, sau restart vẫn `None`),
  `test_omitted_threshold_keeps_saved_override`. Ca cũ (0.30 bị bỏ qua, giá trị trùng ngưỡng hiệu lực không thành ghi
  đè, `min_bm25_score` vẫn nhận) vẫn xanh.
- UI: ca "Dùng giá trị hiệu chỉnh gửi null rồi cập nhật form theo phản hồi" (body `{ guardrails: { min_vector_score:
  null } }`, sau phản hồi huy hiệu về "Đã hiệu chỉnh…", ô 0.37, thanh lưu biến mất).
- Trạng thái: `passed`.

### V-04 — AC-04

- Lệnh: `ConfigView.gate.test.jsx` nhóm "thanh lưu và trường đã sửa"; `ConfigView.cache.test.jsx`.
- Kết quả: không thay đổi → không có thanh lưu, header không còn nút nào; đếm "1/2 thay đổi chưa lưu", tóm tắt
  "Top-K 4→6 · Kiểm soát phạm vi PTIT Bật→Tắt", trường có `is-changed`, "trước: 4", nút `aria-label`
  `Trả "Top-K" về giá trị đã lưu (4)`; mở danh sách đầy đủ; trả từng trường chỉ trả trường đó; "Hủy thay đổi" về
  snapshot và không gọi `fetch`; PUT 422 → toast "CHƯA được lưu", bản nháp và thanh lưu còn; `beforeunload` chỉ
  `preventDefault` khi có thay đổi; cache dùng chung tab Mô hình vẫn giữ bản nháp (3 ca cũ).
- Ảnh: `after-*-top.png` (vạch, "trước: 4", thanh lưu 2 thay đổi).
- Trạng thái: `passed`.

### V-05 — AC-05

- Lệnh: ca "Khôi phục mặc định nằm trong Vùng nguy hiểm…" + ca reset trong `ConfigView.cache.test.jsx`.
- Kết quả: nút ở `.config-danger-zone`, mở hộp thoại "Khôi phục cấu hình mặc định?" có nút "Khôi phục"; reset vẫn đồng
  bộ form. Header không còn nút (ca V-04). Ảnh: `after-desktop-dark-bottom.png`, `after-mobile-light-bottom.png`.
- Trạng thái: `passed`.

### V-06 — AC-06

- Test nhãn: `admin/AdminApp.test.jsx` (sidebar có "Cài đặt"), `models/ModelsView.test.jsx` (ba nhãn loại mô hình mới).
- Thủ công qua ảnh: tiêu đề "Cài đặt", mục sidebar "Cài đặt"; công tắc maroon (sáng: `--brand`, tối: token tối); nút
  "2 lần" nền `--brand-subtle` viền `--brand`; thanh tỷ trọng vector maroon, BM25 xám; nhóm thử lại không viền;
  icon thẻ trung tính; mô tả Top-K có hệ quả + "Mặc định 4". Thanh hệ số ứng viên `max="8"` (đọc mã
  `ConfigView.jsx`, `#cfg-candidate`). Dòng "Ngôn ngữ giao diện" đã xoá khỏi `SettingsView.jsx`.
- Trạng thái: `passed`.

### V-07 — AC-07

- `npm test` (`frontend/`): 37 file, 303/303 passed.
- `npm run build` (`frontend/`): `✓ built in 2.25s`.
- `python -m pytest` (`backend/`, venv): 1346 passed, 24 skipped, 1 warning (StarletteDeprecationWarning có sẵn).
- Ảnh trước (`dev` `a57e4b7`, worktree tạm) và sau (chụp tại `026b8d0`; `415afe3` chỉ đổi xử lý ô số khi gõ, không đổi
  giao diện),
  1366×820 và 390×844, sáng và tối, có 2 thay đổi chưa lưu (Top-K 4→6, ngưỡng cosine 0.37→0.40):
  `docs/design/assets/settings-gate-savebar/{before,after}-{desktop,mobile}-{light,dark}-top.png`, cùng các ảnh
  `*-gate.png` (cuộn tới nhóm ngưỡng) và `after-*-bottom.png` (vùng nguy hiểm).
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chụp đầu, hai dev server (trước/sau) dùng chung `node_modules/.vite` qua junction nên trang "sau" lỗi
  "Invalid hook call"; chạy lại từng server riêng với `--force` thì bình thường. Không phải lỗi sản phẩm.
- Self-review phát hiện R-05 (ô số rỗng khi đang gõ xoá ghi đè) → sửa ở `415afe3`, thêm ca test, chạy lại
  `ConfigView.gate.test.jsx`/`cache`/`configDraft` (30/30) và toàn bộ `npm test` (303/303), `npm run build`.
- Chưa kiểm với backend thật + Postgres (chỉ SQLite tạm trong test và API giả lập trong ảnh).
- Chưa kiểm bằng trình đọc màn hình thật; a11y chỉ kiểm qua thuộc tính (`role`, `aria-*`) trong test.

## Kết luận

- Tiêu chí đã đạt: `AC-01` … `AC-07`.
- Tiêu chí chưa đạt/chưa xác minh: không có.
- Đề xuất: review bản `415afe3`.

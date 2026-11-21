# Verification: 2026-11-21-settings-pipeline-layout

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `feat/settings-pipeline-layout` (nền `43e48f8`), chưa commit.
- Môi trường: Windows 11, Node 24.14.0, Vitest (jsdom), Vite build; ảnh chụp bằng `playwright-core` + Chromium 1234,
  Vite dev `--port 5291`, `/api/**` được mock (config như test, kho 2 mô hình LLM).

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-agent / `2026-11-21T17:33:00+07:00`.
- Loại: test tự động + ảnh chụp.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run`; mở `/admin#settings`, `#settings/gate`, `#settings/models-llm`,
  `#settings/appearance` ở 1440×900.
- Kỳ vọng: không còn `.settings-nav`; header "Cài đặt"; 3 tab có `aria-current="page"` đúng nhóm; hash mở đúng
  tab/bước/loại.
- Kết quả thực tế:
  - Test `SettingsView › mặc định mở tab Hệ thống trả lời…`, `tab Mô hình mở đúng panel…`,
    `SettingsNav › ba tab nhóm…` và `AdminApp › bấm bước Settings đổi hash…` đạt.
  - Ảnh: header + tab, không còn cột danh mục; `#settings/models-llm` mở tab Mô hình, mục "Ngôn ngữ".
- Trạng thái: `passed`.
- Bằng chứng: ảnh `n-desk-retrieval.png`, `n-desk-models.png`, `n-desk-appearance.png` (scratchpad phiên).

### V-02 — AC-02

- Người thực hiện / thời gian: claude-agent / `2026-11-21T17:33:00+07:00`.
- Loại: test tự động + ảnh chụp.
- Lệnh / thao tác: `npx vitest run`; ở ảnh, đổi Top-K 4→6 rồi bấm bước Ngưỡng tin cậy và Sinh câu trả lời.
- Kỳ vọng: chip giá trị theo bản nháp, chấm chưa lưu đúng bước, chỉ form bước đang chọn hiển thị.
- Kết quả thực tế:
  - Đạt: `pipelineSummary.test.js` (5 test), `SettingsView › dải bước hiện giá trị…`, `› bấm bước gọi
    onSectionChange…` (chỉ `settings-section-gate` không ẩn) và `SettingsNav › dải bước theo thứ tự pipeline…`.
  - Ảnh: bước 1 hiện "Top-K 6" kèm chấm cam; tab "Hệ thống trả lời" cũng có chấm.
- Trạng thái: `passed`.
- Bằng chứng: `n-desk-retrieval-dirty.png`, `n-desk-gate.png`.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-agent / `2026-11-21T17:33:00+07:00`.
- Loại: test tự động.
- Lệnh / thao tác: `npx vitest run`.
- Kỳ vọng: đổi bước không mất bản nháp; payload chỉ gồm trường đã đổi.
- Kết quả thực tế:
  - Test mới `SettingsView › đổi bước không mất bản nháp…` đạt: `#cfg-topk` vẫn là 6 khi đang ở bước Sinh câu trả
    lời, thanh lưu báo "1 thay đổi chưa lưu".
  - Toàn bộ `ConfigView.gate.test.jsx` (payload, thanh lưu, trả từng trường, beforeunload, vùng nguy hiểm) và
    `ConfigView.cache.test.jsx` đạt, không sửa test.
  - `AdminApp › 401 giữa chừng… không mất bản nháp Settings` đạt.
- Trạng thái: `passed`.
- Bằng chứng: kết quả `Tests 385 passed (385)`.

### V-04 — AC-04

- Người thực hiện / thời gian: claude-agent / `2026-11-21T17:33:00+07:00`.
- Loại: ảnh chụp.
- Lệnh / thao tác: chụp 1440×900 (sáng, tối), 1100×800 và 390×844.
- Kỳ vọng: section là card có header; nhãn/hint trái, điều khiển phải; công tắc một hàng; khung hẹp xếp một cột.
- Kết quả thực tế:
  - 1440 và 1100: lưới hai cột; công tắc "Bật xếp hạng lại" trải hết hàng (lỗi đặt sai cột ở lần chụp đầu đã sửa);
    tham số phụ cùng lưới.
  - 390: một cột.
- Trạng thái: `passed`.
- Bằng chứng: `n-desk-retrieval.png`, `n-dark-reranker.png`, `n-1100-gate.png`, `n-m-settings_retrieval.png`.

### V-05 — AC-05

- Người thực hiện / thời gian: claude-agent / `2026-11-21T17:33:00+07:00`.
- Loại: test tự động + ảnh chụp.
- Lệnh / thao tác: test `SettingsView › nút Thử với câu hỏi mở ngăn kéo`, `RetrievalTestPanel.test.jsx`; ảnh 1440px
  bấm nút rồi nhấn Esc.
- Kỳ vọng: ngăn kéo bên phải ở 1440px, có scrim; không có nút ở tab Mô hình.
- Kết quả thực tế:
  - Ngăn kéo rộng 480px phủ scrim lên trang.
  - Test focus/Esc của `RetrievalTestPanel` đạt.
  - Ở tab Mô hình `.settings-test-trigger` không tồn tại (test).
- Trạng thái: `passed`.
- Bằng chứng: `n-desk-drawer.png`.

### V-06 — AC-06

- Người thực hiện / thời gian: claude-agent / `2026-11-21T17:33:00+07:00`.
- Loại: test tự động + ảnh chụp.
- Kỳ vọng: thanh chọn 3 loại mô hình mở đúng panel; banner trung tính.
- Kết quả thực tế:
  - Test `SettingsNav › thanh loại mô hình…` và `SettingsView › tab Mô hình…` đạt (`#mdl-panel-embedding` hiện,
    `#mdl-panel-llm` ẩn).
  - `models/ModelsView.test.jsx` đạt.
  - Ảnh: banner nền trắng, viền xám.
- Trạng thái: `passed`.
- Bằng chứng: `n-desk-models.png`.

### V-07 — AC-07

- Người thực hiện / thời gian: claude-agent / `2026-11-21T17:33:00+07:00`.
- Loại: ảnh chụp + đo DOM.
- Lệnh / thao tác: 390×844 mở `#settings`, `#settings/retrieval`, `#settings/models-llm`; đo
  `document.documentElement.scrollWidth` so với `innerWidth`.
- Kỳ vọng: danh sách có giá trị; trang mục có nút quay lại trong header; không cuộn ngang.
- Kết quả thực tế:
  - Danh sách hiện "Top-K 4 · Vector 65% · +3 truy vấn", "BM25 ≥ 0.25 · Cos ≥ 0.37"…
  - Nút "Quay lại Cài đặt" nằm trong header.
  - `scrollWidth` = 390 = `innerWidth` ở cả 3 trang.
- Trạng thái: `passed`.
- Bằng chứng: `n-m-settings.png`, `n-m-settings_retrieval.png`, `n-m-settings_models-llm.png`.

### V-08 — AC-08

- Người thực hiện / thời gian: claude-agent / `2026-11-21T17:33:30+07:00`.
- Loại: test tự động, build.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run`; `npm run build`; `npm run check:bundle`.
- Kỳ vọng: tất cả đạt.
- Kết quả thực tế:
  - `Test Files 46 passed (46)`, `Tests 385 passed (385)`.
  - Build `✓ built in 2.36s`.
  - `check:bundle đạt` (tổng gzip 89.77 kB, mốc 128.41 kB).
- Trạng thái: `passed`.
- Bằng chứng: đầu ra lệnh trong phiên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chụp đầu (V-04): trường "Bật xếp hạng lại" (công tắc không có `bordered-group`) bị lưới đẩy sang cột phải.
  Đã sửa bằng `.config-toggle-header { grid-column: 1 / -1 }`. Chụp lại thì đạt; test chạy lại vẫn 385/385.
- Lần chụp đầu (V-07): nút quay lại nằm ngoài dải header trắng, nút "Thử với câu hỏi" xuống dòng ở 390px. Đã đưa nút
  quay lại vào header và cho dòng "Lần lưu gần nhất" chiếm một hàng. Chụp lại thì đạt.
- `npx eslint` không chạy được vì repo chưa có `eslint.config.*`; không coi là đạt.
- Chưa thử trên Safari/Firefox thật. Container query, `:focus-visible` và `float` trên `legend` đều là tính năng
  chuẩn, nhưng mới chỉ chụp bằng Chromium.

## Kết luận

- Tiêu chí đã đạt: AC-01 … AC-08.
- Tiêu chí chưa đạt/chưa xác minh: không có (ghi chú trình duyệt khác ở trên).
- Đề xuất: bàn giao reviewer.

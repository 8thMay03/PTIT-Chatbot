# Verification: 2026-11-15-settings-nav-retrieval-test

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed` (chạy lại `2026-11-17T21:27:01+07:00` sau sửa R-04).
- Bản được kiểm tra: nhánh `feat/settings-nav-retrieval-test`, commit `7e38924`
  (tách từ `dev` `08f90bb`); lần chạy lại `2026-11-17T21:22:14+07:00` trên working tree `f69d4a0` + bản sửa
  R-03/R-06 chưa commit.
- Môi trường: Windows 11; Node 24.14.0 (Vitest 3.2.7, Vite 5.4.21); Python 3.11.5
  trong `backend/.venv`; Chromium 1234 qua `playwright-core` 1.57.0, API giả lập
  (`/api/**`), dev server Vite `127.0.0.1:5173`.
- Thời điểm: `2026-11-17T21:13:30+07:00`; chạy lại `2026-11-17T21:22:14+07:00`.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Loại: test component + kiểm tra thật trong Chromium.
- Lệnh: `npx vitest run src/settings/SettingsNav.test.jsx src/SettingsView.test.jsx`
  (`frontend/`).
- Kết quả: 11/11 passed. Cột danh mục có đúng ba nhóm "Hệ thống trả lời", "Mô hình",
  "Cá nhân" và tám mục; hash `#settings/<key>` đúng từng mục; `aria-current` theo mục;
  chấm hiện ở mục có trường đã đổi; danh sách mobile có mô tả và gọi `onSelect`.
- Chromium (viewport 390×844): mở `/admin#settings`, danh sách hiện; bấm "Ngưỡng tin
  cậy" → hash `#settings/gate`, nút "Quay lại Cài đặt" hiện, danh sách ẩn, nội dung mục
  hiện; `page.goBack()` → hash `#settings`, danh sách hiện lại, nút quay lại ẩn.
- Chromium (viewport 1366×820): bấm mục "Ngưỡng tin cậy" → hash `#settings/gate`,
  mục có `aria-current="location"`, form cuộn tới đúng anchor.
- Ảnh: `docs/design/assets/settings-nav-retrieval-test/mobile-390-list-{light,dark}.png`,
  `mobile-390-section-{light,dark}.png`, `desktop-1366-{light,dark}.png`.
- Chạy lại `2026-11-17T21:22:14+07:00` (sau sửa R-03):
  - `npx vitest run src/SettingsView.test.jsx src/admin/AdminApp.test.jsx`: 14/14 passed,
    gồm hai test mới cho R-03. Cùng hai test chạy trên mã cũ (`HEAD`) thì thất bại.
  - Chromium 1366×820, dev server `localhost:5191`, API giả lập, script
    `nav-scroll.mjs` trong scratchpad của phiên:
    - `/admin#settings`, cuộn khung form xuống đáy (`scrollTop` 1235), bấm "Truy xuất" → hash
      `#settings/retrieval`, `scrollTop` 0, `history.length` 2 → 3.
    - Cuộn xuống đáy lần nữa rồi bấm lại "Truy xuất" → `scrollTop` 0, `history.length` vẫn 3.
    - Bấm "Sinh câu trả lời" → hash `#settings/generation`, khung cuộn tới đáy (mục này cách
      đỉnh khung 200 px vì form không đủ dài), nhưng `aria-current` nằm ở **"Ngưỡng tin cậy"**
      (`gate`). Đây là R-04 trong `review.md`.
    - Nút Back của trình duyệt → `#settings/retrieval`, `scrollTop` 0.
- Trạng thái lần chạy đó: `failed` — phần cuộn và lịch sử (R-03) đã đạt; `aria-current` sai sau
  khi bấm mục cuối (R-04).
- Chạy lại `2026-11-17T21:27:01+07:00` (sau sửa R-04), cùng script và môi trường Chromium 1366×820:
  - `npx vitest run src/settings/scrollSpy.test.js src/SettingsView.test.jsx
    src/admin/AdminApp.test.jsx src/ConfigView.gate.test.jsx`: 38/38 passed.
  - Bấm lần lượt từng mục, ghi hash / `scrollTop` / `aria-current`:
    - "Sinh câu trả lời" → `#settings/generation` / 1235 / `generation`.
    - "Xếp hạng lại" → `#settings/reranker` / 594 / `reranker`.
    - "Ngưỡng tin cậy" → `#settings/gate` / 840 / `gate`.
    - "Truy xuất" → `#settings/retrieval` / 0 / `retrieval`.
    - "Sinh câu trả lời" lần nữa → `#settings/generation` / 1235 / `generation`.
  - Cuộn tay bằng con lăn (mỗi bước 100 px) từ đầu tới đáy: `retrieval` tới 500, `reranker` ở
    600–700, `gate` ở 800–1200, `generation` ở 1235 (đáy). Không có bước nào đánh dấu sai thứ tự.
  - Tự cuộn tới đáy khi đang ở `#settings` cũng đánh dấu `generation`.
  - R-03 vẫn đạt: bấm "Truy xuất" từ `#settings` và bấm lại cùng mục đều về `scrollTop` 0,
    `history.length` không tăng ở lần bấm lại. Nút Back đúng mục trước đó.
- Trạng thái: `passed`.

### V-02 — AC-02

- Loại: test tự động.
- Lệnh: `npx vitest run src/lib/appRoute.test.js` (`frontend/`) — cũng chạy trong
  `npm test` toàn bộ.
- Kết quả: 34/34 passed. `#settings/config` → `retrieval`; `#settings/models` →
  `models-llm`; `#config` → `retrieval`; `#models` → `models-llm`; key lạ →
  `retrieval`; `readAdminRoute`/`adminRouteHash` khứ hồi cho `#settings` và cả tám key.
  `legacyHashToAdmin` trả `/admin#settings/<key mới>` và vẫn trả `null` cho
  `#settings/appearance`. `App.test.jsx` cập nhật kỳ vọng hash cũ sang key mới.
  `ModelKindPanel` có link `#settings/reranker`.
- Trạng thái: `passed`.

### V-03 — AC-03

- Loại: test component + đo thật trong Chromium.
- Lệnh: `npx vitest run src/ConfigView.gate.test.jsx src/lib/configDraft.test.js`
  (`frontend/`).
- Kết quả: 31/31 passed. Form không còn `.settings-subtabs-header`/lưới hai cột; thứ tự
  section là `retrieval`, `reranker`, `gate`, `generation`; công tắc
  `query_rewrite_use_llm` gửi `{ retrieval: { query_rewrite_use_llm: true } }`; hai dòng
  mô hình trỏ `#settings/models-reranker` và `#settings/models-llm`.
- Đo Chromium 1366×820, trang `#settings/retrieval`: đỉnh `.settings-content` → nhóm
  trường đầu tiên (`.config-field-group` chứa Top-K) = **133 px** (mốc ≤ 140 px).
  Header gộp còn 60 px; slider Top-K ở 206 px tính từ đỉnh vùng nội dung.
- Trạng thái: `passed`.

### V-04 — AC-04

- Loại: test component + kiểm tra Chromium.
- Lệnh: `npx vitest run src/settings/RetrievalTestPanel.test.jsx` (`frontend/`).
- Kết quả: 10/10 passed:
  - câu hỏi rỗng chặn ở client, không gọi `/retrieval/test`;
  - payload đúng `{ query, top_k: 6, dataset_ids: ["ds-1"] }` (Top-K bản nháp, dataset
    đang chọn);
  - kết luận "✕ Sẽ từ chối" + lý do tiếng Việt từ `below_vector`; ba tín hiệu có giá
    trị/ngưỡng; kết quả có câu hỏi viết lại, truy vấn phụ, nguồn "Sổ tay sinh viên D26",
    "Điều 5 · Khoản 2", điểm `cos 0.33 · bm25 0.40 · rerank 3.00`;
  - ngưỡng rerank `null` ghi "không áp dụng" và không có thanh;
  - chạy lại khi đang chạy: request đầu bị abort (`signal.aborted === true`), chỉ kết
    quả thứ hai hiện;
  - Esc đóng drawer và trả focus.
- Chromium 390×844: drawer mở bằng nút "Thử với câu hỏi"; sau 12 lần Tab, focus vẫn
  nằm trong `.retrieval-test-panel`; Esc đóng drawer. Ở 1024×768 bảng là drawer; ở
  1366×820 bảng là cột phải.
- Trạng thái: `passed`.

### V-05 — AC-05

- Loại: test tự động + kiểm tra Chromium.
- Lệnh: `npx vitest run src/lib/gateDecision.test.js
  src/settings/RetrievalTestPanel.test.jsx` (`frontend/`).
- Kết quả: 19/19 passed. Bộ ca `gateDecision.test.js` chép từ
  `backend/tests/test_retrieval_confidence.py`: đạt mọi tín hiệu, trượt từng tín hiệu
  (`below_bm25_norm`, `below_vector`, `below_rerank`), thiếu tín hiệu, bỏ tín hiệu có
  ngưỡng `null` (`passed_uncalibrated_model`), `no_context`, điểm top-1 là max.
  `draftGateThresholds` dùng bảng hiệu chỉnh, bỏ rerank khi provider không phải
  Cross-Encoder, ngưỡng nháp thành `override`. Panel hiện "Bản nháp: ✓ Sẽ trả lời" khi
  ngưỡng nháp 0.30 khác ngưỡng đã lưu 0.37, không hiện khi trùng; ghi "Cần lưu rồi chạy
  lại để thấy ảnh hưởng" khi đổi tỷ trọng; giữ tối đa 5 lần chạy.
- Trạng thái: `passed`.

### V-06 — AC-06

- Loại: test backend + frontend.
- Lệnh: `python -m pytest tests/test_config_api.py tests/test_config_persistence.py -q`
  (`backend/.venv`).
- Kết quả: 39/39 passed. Ca mới:
  - `GET /config` trả `updated_at = null` trước lần lưu đầu, sau đó là ISO 8601 có múi
    giờ;
  - lưu → xoá dòng ghi đè (đưa trường về `.env`) → `updated_at` vẫn đổi;
  - `POST /config/reset` ghi mốc mới dù bảng override rỗng;
  - dòng metadata sống qua `_simulate_restart()` và không bị `load_overrides` coi là
    override (`applied` chỉ gồm trường thật);
  - `query_rewrite_use_llm` PUT/GET khứ hồi.
- Frontend: `src/settings/relativeTime.test.js` 5/5 (hôm nay, hôm qua, trong năm, khác
  năm, chưa lưu/hỏng) và `SettingsView.test.jsx` xác nhận header hiện "Lần lưu gần nhất:
  … hôm nay".
- Trạng thái: `passed`.

### V-07 — AC-07

- Lệnh và kết quả cuối trên commit `7e38924` (chạy lại sau khi thêm dấu "—" vào dòng
  mô hình):
  - `npm test` (`frontend/`): **42 file, 343/343 test passed**.
  - `npm run build` (`frontend/`): thành công (`✓ built in 2.41s`).
  - `npm run check:bundle` (`frontend/`): **đạt**; JS ban đầu trang chat 84.49 kB gzip,
    dưới mốc FE-06 128.41 kB; không có module Settings/admin trong chunk chat.
  - `python -m pytest` (`backend/`, venv): **1351 passed, 24 skipped, 1 warning**
    (StarletteDeprecationWarning có sẵn).
- Ảnh (sáng + tối, có kết quả thử và thay đổi chưa lưu):
  - 1366×820: `desktop-1366-light.png`, `desktop-1366-dark.png`.
  - 1024×768: `tablet-1024-light.png`, `tablet-1024-dark.png` (drawer mở, có kết quả).
  - 390×844: `mobile-390-list-{light,dark}.png` (danh sách mục);
    `mobile-390-section-{light,dark}.png` (trang mục, 2 thay đổi chưa lưu);
    `mobile-390-{light,dark}.png` (drawer có kết quả).
  - Thư mục: `docs/design/assets/settings-nav-retrieval-test/`.
- Chạy lại `2026-11-17T21:22:14+07:00` trên working tree có bản sửa R-03/R-06:
  - `npm test` (`frontend/`): **42 file, 345/345 test passed** (thêm 2 test cho R-03).
  - `npm run build`: thành công (`✓ built in 2.28s`).
  - `npm run check:bundle`: **đạt**; JS ban đầu trang chat 84.50 kB gzip, dưới mốc 128.41 kB.
  - Backend không đổi từ `7e38924`. Không chạy lại toàn bộ `pytest`; review vòng 3 đã chạy lại
    4 file liên quan (82 passed).
  - Ảnh chưa chụp lại: bản sửa không đổi bố cục; câu chữ ghi chú trong bảng thử khác ảnh cũ.
- Chạy lại `2026-11-17T21:27:01+07:00` sau sửa R-04:
  - `npm test` (`frontend/`): **43 file, 350/350 test passed** (thêm `scrollSpy.test.js`).
  - `npm run build`: thành công (`✓ built in 2.12s`).
  - `npm run check:bundle`: **đạt**; 84.50 kB gzip, dưới mốc 128.41 kB.
  - Backend vẫn không đổi; không chạy lại `pytest` toàn bộ.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy đầu của bộ test panel: nút "Chạy thử" bị `disabled` khi đang chạy nên không
  thể "chạy lại để huỷ request cũ" (trái AC-04). Đã bỏ `disabled`, thêm `title`/`aria-label`
  "Chạy lại (huỷ lần đang chạy)", test huỷ request qua.
- Ảnh chụp dùng API giả lập (như task `settings-gate-savebar`) để kiểm tra bố cục và
  tương tác; không chứng minh chất lượng truy xuất thật. Phần này phụ thuộc dữ liệu và
  embedding của môi trường chạy.
- Scrollspy/đo khoảng cách/Back/drawer được kiểm tra thủ công bằng Chromium, không đưa
  vào jsdom.

## Kết luận

- Tiêu chí đã đạt: `AC-01` … `AC-07` (AC-01 xác nhận lại sau sửa R-03/R-04).
- Tiêu chí chưa đạt/chưa xác minh: không. Giới hạn: ảnh chụp chưa làm lại theo câu chữ R-06;
  `pytest` toàn bộ chưa chạy lại vì backend không đổi.
- Đề xuất: commit bản sửa, cập nhật mã commit trong các file task.

# Implementation: 2026-11-15-settings-gate-savebar

## Tổng quan triển khai

- Nhánh `feat/settings-gate-savebar`, tách từ `dev` tại `a57e4b7` (đã `git fetch`, `dev` trùng `origin/dev`).
- Working tree lúc tách nhánh có sẵn thay đổi không thuộc task này (xoá `data/Sổ tay sinh viên D26 _1_.pdf`, các thư
  mục task/tài liệu nghiên cứu chưa track). Tạo nhánh bằng `git checkout -b` không đụng tới chúng; không commit,
  không stash.
- Commit:
  - `2f7260b` feat: clear gate threshold overrides with explicit null in PUT /config (S-01)
  - `ac92a3d` feat: align RAG settings gate thresholds and add contextual save bar (S-02, S-03)
  - `026b8d0` feat: use Vietnamese labels for settings and model kinds (S-04)
  - `415afe3` fix: ignore partial threshold input instead of clearing the override (sửa R-05 khi self-review)
  - commit ghi nhật ký task + ảnh (S-05) ngay sau các commit trên.

## Nhật ký theo nhiệm vụ

### S-01 — Backend (`done`)

- `backend/app/core/config.py` `update_runtime_config`: `guardrails.min_vector_score`/`min_rerank_score` có khoá và
  giá trị `null` → đặt settings về `_INITIAL_SETTINGS[...]` (giá trị `.env` lúc khởi động); `save_overrides` xoá dòng
  vì giá trị bằng ban đầu. Không có khoá → giữ nguyên. Giá trị số giữ nguyên luật cũ (bỏ qua 0.30 và giá trị trùng
  ngưỡng hiệu lực).
- `get_runtime_config_dict()` + `GuardrailsConfigPayload` thêm 3 trường **bổ sung** (không đổi/xoá trường cũ):
  `calibrated_min_vector_score`, `rerank_threshold_source`, `calibrated_min_rerank_score`. Xem quyết định D-1.
- Test: `test_config_api.py` +4 (xoá ghi đè vector, vector trên model chưa hiệu chỉnh, xoá ghi đè rerank, không gửi
  thì giữ nguyên); `test_config_persistence.py` +2 (xoá dòng DB và còn sau restart; không gửi thì dòng còn).

### S-02 — Nhóm Ngưỡng tin cậy + payload một phần (`done`)

- `frontend/src/lib/configDraft.js`: chuyển `DEFAULTS`/`valuesFromConfig` vào đây; thêm `CONFIG_FIELDS` (nhãn, đường
  dẫn payload, định dạng), `calibratedFromConfig`, `formatConfigValue`, `isFieldChanged`, `listConfigChanges`,
  `buildConfigPayload`. Bản nháp ngưỡng vector/rerank là **ghi đè** (`null` = theo bảng hiệu chỉnh), không còn rơi về
  0.30; bỏ hẳn `minBm25Score`; thêm `minBm25NormScore`.
- `ConfigView.jsx`: nhóm "Ngưỡng tin cậy" gồm khối mô tả cơ chế (đoạn khớp nhất, trượt bất kỳ ngưỡng → "Chưa tìm thấy
  thông tin này trong tài liệu.", không gọi mô hình), "Độ khớp từ khóa tối thiểu" (0–1, bước 0.01), "Độ tương đồng
  ngữ nghĩa tối thiểu" với huy hiệu `Đã hiệu chỉnh cho <model>` / `Ghi đè` / cảnh báo chưa hiệu chỉnh (ô trống, ẩn
  thanh trượt), link "Dùng giá trị hiệu chỉnh (x.xx)" (hoặc "Bỏ ghi đè…" khi model chưa hiệu chỉnh) đặt bản nháp về
  `null` → lưu gửi `null`. "Điểm xếp hạng lại tối thiểu" chỉ hiện khi bản nháp bật reranker và provider (từ `/config`)
  là `cross-encoder`; trường hợp khác hiện một dòng "không áp dụng…".
- Lưu: `configApi.update(buildConfigPayload(values, savedSnapshot))` — chỉ trường đã đổi.
- Kéo thanh trượt về đúng giá trị hiệu chỉnh khi đang không ghi đè thì giữ `null` (không tạo thay đổi giả).

### S-03 — Thanh lưu, đánh dấu trường, vùng nguy hiểm (`done`)

- `frontend/src/components/SaveBar.jsx` (dùng lại được ở giai đoạn 2): props `changes`, `onDiscard`, `onSave`,
  `saving`, `disabled`; `role="region"` + `aria-label="Thay đổi chưa lưu"`; "<N> thay đổi chưa lưu", tóm tắt
  `nhãn cũ→mới`, bấm để mở danh sách đầy đủ (`aria-expanded`); nút "Hủy thay đổi" và "Lưu".
- Thanh nằm ngoài vùng cuộn (flex con cuối của `.config-page-wrapper`) nên không che trường cuối; ≤900px rộng toàn
  panel, ≤600px nút cao 44px chia đôi.
- Header panel bỏ huy hiệu "Có thay đổi chưa lưu", nút "Mặc định", nút "Lưu cấu hình".
- Mỗi trường đã sửa: lớp `is-changed` (vạch `--warning` mép trái), "trước: <giá trị>", nút ↺ có `aria-label`
  `Trả "<nhãn>" về giá trị đã lưu (<giá trị>)`.
- Thẻ "Vùng nguy hiểm" cuối form với nút "Khôi phục mặc định…" mở `Modal` tông `danger` có sẵn.
- `beforeunload`, giữ bản nháp khi lưu lỗi, `mergeConfigDraft` với cache dùng chung: giữ nguyên.
- `styles/responsive.css`: xoá hai luật `.settings-header-actions` không còn phần tử nào dùng (ngoài danh sách file
  trong plan, thay đổi chỉ là xoá CSS chết do chính task này tạo ra).

### S-04 — Nhãn và thị giác (`done`)

- "Settings" → "Cài đặt" (H1 `SettingsView`, mục sidebar + `title` trong `AdminShell`).
- `models/catalog.js`: "Mô hình ngôn ngữ (LLM)", "Mô hình nhúng (Embedding)", "Mô hình xếp hạng lại (Reranker)".
- `config.css`: công tắc trong form cấu hình `--brand` (override trong `.config-page-wrapper`, `dataset.css` không
  đổi); nút chọn số lần thử lại `--brand-subtle/--brand`; thanh tỷ trọng vector `--brand`, BM25 trung tính; icon thẻ
  trung tính; fieldset nhóm thử lại bỏ viền.
- Thanh hệ số ứng viên 1–8; bỏ dòng "Ngôn ngữ giao diện"; mô tả Top-K "Nhiều đoạn hơn giúp đủ ngữ cảnh nhưng tăng độ
  trễ và chi phí. Mặc định 4." (thêm mặc định cho temperature, thời gian chờ, tỷ trọng).
- Đổi nhãn "Dùng LLM để viết lại truy vấn" → "Dùng LLM để sinh truy vấn phụ" vì công tắc này là
  `multi_query_use_llm`, không phải `query_rewrite_use_llm`.
- Test cập nhật: `admin/AdminApp.test.jsx`, `models/ModelsView.test.jsx`, `ConfigView.cache.test.jsx`.

### S-05 — Kiểm chứng và ảnh (`done`)

- Xem `verification.md`. Ảnh: `docs/design/assets/settings-gate-savebar/` (16 ảnh, 1.2 MB).

## Quyết định

- **D-1** (`claude-agent`, coordinator): thêm 3 trường bổ sung vào `guardrails` của GET/PUT `/config` dù plan ghi
  "Không đổi schema response". Lý do: AC-03 yêu cầu link "Dùng giá trị hiệu chỉnh (<giá trị>)" khi đang ghi đè, lúc đó
  response chỉ có ngưỡng ghi đè, không có giá trị bảng hiệu chỉnh; và AC-01 cần biết ngưỡng rerank đang ghi đè hay
  hiệu chỉnh. Trường mới là tuỳ chọn, client cũ bỏ qua được; không đổi trường cũ.
- **D-2**: link "Dùng giá trị hiệu chỉnh" đổi bản nháp (hiện trong thanh lưu) chứ không lưu ngay, để mọi thay đổi đi
  qua cùng một nút Lưu/Hủy.
- **D-3**: ô số ngưỡng bỏ qua chuỗi rỗng/dở dang khi đang gõ; bỏ ghi đè chỉ qua link (tránh nhảy về giá trị hiệu chỉnh
  khi gõ "0.").

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

- Đã làm: S-01 … S-05 trên `feat/settings-gate-savebar` (commit ở trên).
- Ảnh hưởng task sau (`2026-11-15-settings-nav-retrieval-test`): `ConfigView.jsx` đã tách logic bản nháp sang
  `lib/configDraft.js`; `SaveBar` sẵn để dùng cho form một cột; ngưỡng nháp là ghi đè (`null` = hiệu chỉnh), giá trị
  hiệu lực = `values.minVectorScore ?? calibrated.vector`.
- Kiểm tra: `npm test` 303/303, `npm run build` OK, `python -m pytest` 1346 passed / 24 skipped.
- ~~Chưa làm: chưa push, chưa mở PR vào `dev` — chờ người dùng đồng ý.~~ `2026-11-17T20:15:42+07:00`: đã push nhánh
  và mở PR #71 vào `dev` (https://github.com/8thMay03/PTIT-Chatbot/pull/71) theo yêu cầu người dùng; chưa merge.
- Việc theo dõi cho task `2026-11-15-settings-nav-retrieval-test`: R-07, R-08, R-09 (và R-01) trong `review.md`.

# Implementation: 2026-11-15-settings-nav-retrieval-test

## Tổng quan triển khai

- Nhánh `feat/settings-nav-retrieval-test`, tách từ `dev` tại `08f90bb` (sau khi
  `2026-11-15-settings-gate-savebar` merge qua PR #71).
- Commit triển khai: `7e38924` — `feat: add settings navigation and retrieval test panel`.
- Hoàn thành S-01 … S-04; S-05 ghi bằng chứng trong `verification.md`.
- Working tree còn thay đổi không liên quan của người dùng:
  `data/Sổ tay sinh viên D26 _1_.pdf` bị xoá và các task/tài liệu nghiên cứu chưa
  commit của các phiên trước. Không khôi phục, không commit, không sửa.

## Nhật ký theo nhiệm vụ

### S-01 — Route và khung danh mục dọc (`done`)

- `frontend/src/lib/appRoute.js`:
  - Thêm `ADMIN_ANSWER_SECTIONS`, `ADMIN_MODEL_SECTIONS`, `ADMIN_SETTINGS_SECTIONS`,
    `normalizeSettingsSection`, `modelKindForSection`.
  - Route admin đổi `{ view, tab, datasetId }` → `{ view, section, datasetId }`.
  - `#settings/config`/`#config` → `retrieval`; `#settings/models`/`#models` →
    `models-llm`; key lạ → `retrieval`; `#settings` (không key) giữ `section: null`.
  - `legacyHashToAdmin` trả `/admin#settings/<key mới>`; `#settings/appearance` vẫn
    trả `null` để app sinh viên mở bộ chọn giao diện tại chỗ.
- `frontend/src/admin/AdminShell.jsx`: route dùng `section`; đổi mục Settings bằng
  `history.pushState` + `setRoute` nên nút Back của trình duyệt hoạt động; vào
  Settings từ thanh bên mở `#settings` (mobile: danh sách).
- Mới `frontend/src/settings/SettingsNav.jsx`: `SettingsSidebar` (ba nhóm, anchor
  `#settings/<key>`, `aria-current`, chấm thay đổi) và `SettingsIndex` (danh sách
  toàn màn hình cho mobile).
- `frontend/src/SettingsView.jsx`: bố cục ba cột `nav | nội dung | bảng thử` ở
  ≥1280px, hai cột ở <1280px, một cột ở <1024px; panel luôn mounted; header hiện
  "Lần lưu gần nhất"; nút quay lại ở mobile.
- `frontend/src/ModelsView.jsx`: bỏ tab con/localStorage `ptit_models_tab`, nhận
  `kind` từ route, giữ cả ba panel mounted và dọn khoá cũ.
- `frontend/src/models/ModelKindPanel.jsx`: link "Bật trong Cài đặt" đổi sang
  `#settings/reranker`.

### S-02 — Form "Hệ thống trả lời" (`done`)

- `frontend/src/ConfigView.jsx`:
  - Bỏ header panel cũ và lưới 2 cột; một cột tối đa 720px theo thứ tự Truy xuất →
    Xếp hạng lại → Ngưỡng tin cậy → Sinh câu trả lời.
  - Mỗi mục có `id="settings-section-<key>"` + `scroll-margin-top`; scrollspy bằng
    `IntersectionObserver` (bỏ qua trong jsdom), nhận `activeSection` từ route để
    cuộn tới anchor khi deep link/đổi mục.
  - Thêm công tắc `query_rewrite_use_llm` ("Viết lại câu hỏi bằng LLM").
  - Dòng "Mô hình: … — Đổi mô hình →" cho Xếp hạng lại và Sinh câu trả lời.
  - Báo `dirtySections`, `changedKeys`, giá trị nháp và `config` lên `SettingsView`
    qua `onDraftState`.
- `frontend/src/lib/configDraft.js`: thêm `queryRewriteUseLlm`, gắn `section` cho
  từng trường, thêm `listDirtySections`.
- CSS trong `frontend/src/styles/config.css` và `responsive.css`: bỏ style tab cũ,
  thêm bố cục Settings, form pipeline, bảng thử/drawer; header rút còn 60px.

### S-03 — Bảng "Thử với câu hỏi" (`done`)

- Mới `frontend/src/api/retrieval.js` (`POST /retrieval/test`, timeout 120s) và
  export `retrievalApi` trong `frontend/src/api/index.js`.
- Mới `frontend/src/lib/gateDecision.js`: bản sao thuần của `assess_context`
  (`confidence.py`), thứ tự `bm25_norm` → `vector` → `rerank`, thiếu tín hiệu tính
  trượt, ngưỡng `null` bỏ qua, `passed_uncalibrated_model` khi bỏ tín hiệu vector.
- Mới `frontend/src/settings/RetrievalTestPanel.jsx`:
  - Cột phải ở ≥1280px; <1280px là drawer có scrim, focus trap, Esc, trả focus.
  - Ô câu hỏi, chọn dataset (`GET /api/datasets`, mặc định tất cả), `top_k` lấy từ
    Top-K bản nháp.
  - Kết luận đã lưu + lý do tiếng Việt; ba thanh tín hiệu có vạch ngưỡng đã lưu và
    vạch nháp; "không áp dụng" khi ngưỡng `null`.
  - Câu hỏi viết lại, truy vấn phụ, danh sách đoạn kèm nguồn, Điều/Khoản/Điểm và
    `cos`/`bm25`/`rerank`.
  - Câu hỏi rỗng chặn ở client; 503/mạng qua `describeError`; 401 đi qua lớp phủ
    phiên hiện có.
  - Chạy lại khi đang chạy: `AbortController` huỷ request cũ; giữ tối đa 5 lần chạy
    trong phiên và cho chọn lại từng lần.
  - "Bản nháp: Sẽ trả lời/Sẽ từ chối" khi ngưỡng nháp khác bản đã lưu; ghi "Cần lưu
    rồi chạy lại để thấy ảnh hưởng" khi đổi tỷ trọng/mở rộng câu hỏi/reranker/phạm vi.

### S-04 — Backend `updated_at` (`done`)

- `backend/app/core/config_store.py`:
  - Dòng metadata `__settings_saved_at__` (ngoài `PERSISTED_FIELDS`) ghi ISO 8601
    UTC mỗi lần `save_overrides` (kể cả khi lần lưu chỉ xoá dòng ghi đè) và mỗi lần
    `reset_config`.
  - `load_overrides` bỏ qua dòng này; `read_saved_at` trả `datetime` có múi giờ
    hoặc `None`, không làm hỏng `GET /config` khi DB lỗi.
- `backend/app/api/schemas.py`: `FullConfigResponse.updated_at: datetime | None`.
- `backend/app/api/routes.py`: `GET`/`PUT`/`POST /config/reset` trả `updated_at`.
- Không cần migration Alembic: dùng dòng mới trong bảng `app_config_overrides` sẵn có.

### Sửa sau review vòng 3 — R-03, R-06 (`done`, commit `6cc36b7`)

- R-03 (bấm mục không cuộn khi route không đổi):
  - `frontend/src/SettingsView.jsx`: thêm bộ đếm `scrollRequest`, tăng mỗi lần
    `handleSelect` chọn một mục thuộc `ADMIN_ANSWER_SECTIONS`, truyền xuống `ConfigView`.
  - `frontend/src/ConfigView.jsx`: nhận prop `scrollRequest`; effect cuộn tới anchor phụ
    thuộc `[activeSection, scrollRequest, loading]`. Deep link/hashchange vẫn cuộn như trước.
  - `frontend/src/admin/AdminShell.jsx`: `openSettingsSection` chỉ `pushState` khi hash mới
    khác hash hiện tại. Bấm lại mục đang mở không còn thêm mục lịch sử trùng.
  - Test mới: `SettingsView.test.jsx` ("bấm Truy xuất khi đang ở #settings…", hai lần bấm
    liên tiếp đều cuộn); `admin/AdminApp.test.jsx` ("bấm lại mục Settings đang mở…": cuộn
    lần nữa, `history.length` không tăng). Cả hai test thất bại trên mã cũ và đạt sau khi sửa.
- R-06 (câu chữ):
  - `frontend/src/settings/RetrievalTestPanel.jsx`: hai ghi chú ghi rõ "Chạy trên cấu hình đã
    lưu, riêng Top-K lấy theo bản nháp"; bỏ Top-K khỏi danh sách cần lưu rồi chạy lại, thêm
    "mở rộng câu hỏi" cho khớp `NEEDS_SAVED_RUN_KEYS`.
  - `frontend/src/lib/gateDecision.js`: sửa comment `DEFAULT_GATE_THRESHOLDS` (chỉ tín hiệu
    từ khóa; vector/rerank `null`).

### Sửa sau review vòng 4 — R-04 (`done`, commit `6cc36b7`)

- Mới `frontend/src/settings/scrollSpy.js`: hàm thuần `pickActiveSection`. Mục đang xem là mục
  cuối cùng có tiêu đề đã qua vạch 64 px tính từ đỉnh khung cuộn; cuộn tới đáy (và khung cuộn
  được) thì luôn là mục cuối.
- `frontend/src/ConfigView.jsx`: bỏ `IntersectionObserver` với dải `-12% … -70%`. Scrollspy giờ
  nghe sự kiện `scroll` của khung form, gộp theo `requestAnimationFrame`, đo vị trí bốn mục rồi
  gọi `pickActiveSection`. Chỉ chạy khi có sự kiện cuộn nên lúc mount mục đang xem vẫn theo route.
- Mới `frontend/src/settings/scrollSpy.test.js` (5 ca, số đo lấy gần form thật ở 1366×820: khung
  700 px, cuộn tối đa 1235 px, mục cuối cách đỉnh 200 px khi ở đáy).
- Quyết định: chọn quy tắc "cuộn tới đáy = mục cuối" thay vì khoá scrollspy sau khi bấm. Quy tắc
  này đúng cả khi người dùng tự cuộn tới đáy, và không cần trạng thái phân biệt cuộn do bấm với
  cuộn tay.

## Quyết định

- `#settings` không kèm key là trạng thái hợp lệ: desktop hiện form mặc định
  (Truy xuất), mobile hiện danh sách mục. Nhờ vậy nút Back từ trang mục trở về danh
  sách mà không cần state ngoài URL.
- Bấm mục danh mục dùng `pushState`; scrollspy chỉ đổi `aria-current`, không ghi
  hash, tránh làm rác lịch sử khi cuộn.
- Bảng thử giữ mounted khi đổi mục để không mất 5 lần chạy; chỉ tải dataset khi
  nhóm "Hệ thống trả lời" đang mở.
- `updated_at` phải là nguồn riêng: `max(app_config_overrides.updated_at)` không đủ
  khi lần lưu xoá dòng hoặc reset xoá sạch bảng.
- Không đổi `POST /retrieval/test` (đúng phạm vi: ghi đè tham số nháp là task sau).

## Trao đổi giữa các agents

- Không có agent khác trong phiên này; không có trao đổi cần phản hồi.

## Bàn giao

- Nhiệm vụ đã làm: S-01 … S-05.
- File/commit: nhánh `feat/settings-nav-retrieval-test`, commit `7e38924` (triển khai) và `6cc36b7`
  (`fix: scroll and highlight settings sections on every nav click`, sửa R-03/R-04/R-06); ảnh trong
  `docs/design/assets/settings-nav-retrieval-test/`.
- Hợp đồng ảnh hưởng agent khác:
  - `readAdminRoute`/`adminRouteHash` dùng `section` thay cho `tab`.
  - `FullConfigResponse.updated_at` là chuỗi ISO 8601 có múi giờ hoặc `null`.
  - `SettingsView` nhận `section`, `onSectionChange`, `onBackToList`.
- Kiểm tra đã chạy: xem `verification.md`.
- Phần chưa xong: không có trong phạm vi. Đã mở PR #72 vào `dev` (https://github.com/8thMay03/PTIT-Chatbot/pull/72).
- Người nhận: reviewer; bước tiếp theo: review diff nhánh và kết luận.

# Task: Cài đặt quản trị — danh mục dọc theo pipeline và bảng "Thử với câu hỏi"

- ID: `2026-11-15-settings-nav-retrieval-test`
- Trạng thái: `in_review`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("tạo task cải thiện đi", sau tài liệu nghiên cứu màn Cài đặt)
- Tạo lúc: `2026-11-15T23:42:56+07:00`
- Cập nhật lúc: `2026-11-17T21:27:01+07:00`

## Yêu cầu và kết quả mong muốn

Giai đoạn 2 của lộ trình trong `docs/design/Settings-Market-Research.md` §8: đề xuất D-04, D-03 và D-08 (D-08 chuyển từ
giai đoạn 3 sang đây vì dòng "Lần lưu gần nhất" nằm ở header của bố cục mới).

**Hiện trạng** (H-03, H-04, H-05):

- `POST /api/retrieval/test` đã trả `contexts`, `strong_context`, `retrieval_debug` gồm `confidence {reason, signals,
  thresholds}`, `rewritten_query` và `retrieval_queries`, nhưng frontend không gọi, nên quản trị viên chỉnh tham số mà
  không thấy hệ quả.
- Tham số của một khâu nằm rải ở hai tab: bật reranker ở Cấu hình RAG còn mô hình reranker ở Mô hình; temperature ở Cấu
  hình RAG còn mô hình LLM ở Mô hình.
- Lưới 2 cột làm thứ tự đọc zigzag.
- `query_rewrite_use_llm` có trong API nhưng không có trên UI.
- Tiêu đề trang, thanh tab và header panel chiếm khoảng 230px chiều cao trước trường đầu tiên.

**Kết quả cần có**:

- Danh mục dọc gồm ba nhóm. Mỗi mục có hash riêng.
  - "Hệ thống trả lời": Truy xuất, Xếp hạng lại, Ngưỡng tin cậy, Sinh câu trả lời. Đây là một form, một nút lưu, các
    mục là anchor.
  - "Mô hình": ngôn ngữ, nhúng, xếp hạng.
  - "Cá nhân": Giao diện.
- Form một cột theo thứ tự pipeline.
- Bảng "Thử với câu hỏi" cạnh form: kết luận sẽ trả lời hay từ chối, điểm so ngưỡng, các đoạn tìm được; so ngưỡng nháp
  tại chỗ.
- Header hiện "Lần lưu gần nhất".

Mockup tham chiếu: `docs/design/mockups/settings-proposed.html` khung A.

## Phạm vi

- Bao gồm:
  - Frontend:
    - `frontend/src/SettingsView.jsx`, `frontend/src/admin/AdminShell.jsx`.
    - `frontend/src/lib/appRoute.js` (+ `appRoute.test.js`).
    - `frontend/src/ConfigView.jsx`, `frontend/src/ModelsView.jsx`, `frontend/src/models/ModelKindPanel.jsx` (link chéo).
    - `frontend/src/styles/config.css`, `frontend/src/styles/responsive.css`.
    - Component mới: thư mục `frontend/src/settings/` (ví dụ `SettingsNav.jsx`, `RetrievalTestPanel.jsx`).
    - `frontend/src/lib/gateDecision.js` (+ test), `frontend/src/api/retrieval.js` + export trong `api/index.js`.
    - Test liên quan (`admin/AdminApp.test.jsx`, `models/ModelsView.test.jsx`, `ConfigView.*.test.jsx`, `App.test.jsx`).
  - Backend:
    - `backend/app/api/schemas.py` (`FullConfigResponse.updated_at`), `backend/app/api/routes.py` (`_config_response`).
    - `backend/app/core/config_store.py` (nguồn thời điểm lưu).
    - Migration Alembic mới nếu cần bảng/cột.
    - Test `backend/tests/test_config_api.py`, `test_config_persistence.py`.
- Ngoài phạm vi:
  - Cho `/retrieval/test` nhận tham số nháp (D-03 giai đoạn 2, task sau nếu cần).
  - Preset (D-07), hướng dẫn đổi embedding từng bước (D-09), cài đặt sinh viên.
  - Đổi luật gate.
- Ràng buộc:
  - Bắt đầu sau khi `2026-11-15-settings-gate-savebar` đã merge vào `dev`, vì task này dùng thanh lưu, nhóm Ngưỡng tin
    cậy và nhãn mới của task đó, và cùng sửa `ConfigView.jsx`, `config.css`.
  - Hash cũ (`#settings/config`, `#settings/models`, `#config`, `#models`, link cũ từ app sinh viên) vẫn dẫn tới màn
    tương ứng.
  - `#settings/appearance` ở app sinh viên vẫn mở bộ chọn giao diện tại chỗ.
  - Không trộn hai kiểu lưu trong một form: nhóm "Hệ thống trả lời" lưu tường minh bằng thanh lưu; các mục "Mô hình" giữ
    nút riêng (thêm/sửa/xoá/dùng mô hình).
  - Giữ bản nháp khi chuyển mục (form luôn mounted như hiện tại).
  - Chunk trang chat sinh viên không được chứa mã Settings (`npm run check:bundle`).
  - Nhánh `feat/settings-nav-retrieval-test` tách từ `dev`; commit message tiếng Anh.

## Tiêu chí nghiệm thu

- [x] AC-01: Ở chiều rộng ≥ 1024px, Settings có cột danh mục dọc ba nhóm như mục "Kết quả cần có".
  - Mỗi mục ứng với hash `#settings/<key>`, key thuộc `retrieval`, `reranker`, `gate`, `generation`, `models-llm`,
    `models-embedding`, `models-reranker`, `appearance`.
  - Bấm mục thì đổi hash. Trong nhóm "Hệ thống trả lời", bấm mục thì cuộn tới anchor; khi cuộn, mục đang xem được đánh
    dấu (`aria-current`).
  - Mục có thay đổi chưa lưu hiện chấm.
  - Dưới 1024px, danh mục thành danh sách; chọn mục thì mở trang mục đó, có nút quay lại; nút Back của trình duyệt hoạt
    động.
- [x] AC-02: Ánh xạ hash cũ có test trong `appRoute.test.js`:
  - Admin: `#settings/config` → `retrieval`, `#settings/models` → `models-llm`, `#config` → `retrieval`, `#models` →
    `models-llm`; key lạ → `retrieval`.
  - App sinh viên: hash cũ chuyển sang `/admin#settings/<key mới>`; `#settings/appearance` vẫn mở bộ chọn giao diện tại
    chỗ.
  - Link "Bật trong Cấu hình RAG" ở `ModelKindPanel.jsx` trỏ tới `#settings/reranker`.
- [x] AC-03: Form "Hệ thống trả lời":
  - Một cột, rộng tối đa khoảng 720px, thứ tự Truy xuất → Xếp hạng lại → Ngưỡng tin cậy → Sinh câu trả lời.
  - Có công tắc `query_rewrite_use_llm` ("Viết lại câu hỏi bằng LLM").
  - Mục Xếp hạng lại và Sinh câu trả lời có dòng "Mô hình: <tên> — Đổi mô hình →" dẫn tới mục mô hình tương ứng.
  - Tiêu đề trang và header panel cũ được gộp; khoảng cách từ đỉnh vùng nội dung tới trường đầu tiên ở 1366×820 không
    quá 140px.
  - Lưới 2 cột cũ được bỏ.
- [x] AC-04: Bảng "Thử với câu hỏi":
  - Vị trí: cột phải ở ≥ 1280px; drawer mở bằng nút ở chiều rộng nhỏ hơn, có focus trap và Esc.
  - Đầu vào: ô câu hỏi, chọn dataset (từ `GET /api/datasets`, mặc định tất cả), nút "Chạy thử". Bấm thì gọi
    `POST /api/retrieval/test` với `query`, `dataset_ids`, `top_k` (giá trị Top-K đang hiện trên form).
  - Kết quả:
    - Kết luận "Sẽ trả lời"/"Sẽ từ chối", lý do ánh xạ từ `confidence.reason` sang câu tiếng Việt.
    - Ba tín hiệu, mỗi tín hiệu là một thanh có vạch ngưỡng. Tín hiệu không áp dụng (ngưỡng `null`) ghi rõ "không áp
      dụng".
    - Câu hỏi viết lại và các truy vấn phụ.
    - Danh sách đoạn kèm tên nguồn, điều/khoản nếu có, điểm `vector_score`/`bm25_norm_score`/`rerank_score`.
  - Lỗi: query rỗng chặn ở client; 503 embedding chưa sẵn sàng và lỗi mạng hiện qua `describeError`; 401 đi theo lớp phủ
    hết phiên hiện có.
  - Chạy lại khi đang chạy thì huỷ request cũ.
- [x] AC-05: So ngưỡng nháp:
  - Khi bản nháp có ngưỡng khác bản đã lưu, bảng hiện thêm "Bản nháp: Sẽ trả lời/Sẽ từ chối".
  - Kết luận này tính bằng hàm thuần `lib/gateDecision.js` (AND trên các ngưỡng khác `null`, thiếu tín hiệu tính là
    trượt, thứ tự lý do giống `confidence.py`). Có test với bộ ca tương ứng `backend/tests/test_retrieval_confidence.py`.
  - Bản nháp đổi tỷ trọng, mở rộng câu hỏi hoặc reranker thì bảng ghi "Cần lưu rồi chạy lại để thấy ảnh hưởng".
  - Giữ tối đa 5 lần chạy gần nhất trong phiên để so trước/sau.
- [x] AC-06: "Lần lưu gần nhất":
  - `GET`/`PUT /config` trả `updated_at` (ISO 8601 có múi giờ, `null` khi chưa từng lưu), phản ánh lần lưu hoặc khôi
    phục mặc định gần nhất, kể cả khi lần lưu đó chỉ xoá dòng ghi đè.
  - Header hiện thời điểm dạng tương đối ("14:02 hôm nay").
  - Có test backend (lưu, xoá ghi đè, reset, lưu bền qua khởi động lại) và test frontend.
- [x] AC-07: Kiểm tra cuối:
  - `npm test`, `npm run build`, `npm run check:bundle` (`frontend/`) và `python -m pytest` (`backend/`) xanh.
  - Có ảnh chụp ở 1366×820, 1024×768, 390×844, sáng và tối, gồm trạng thái có kết quả thử và có thay đổi chưa lưu.

## Tài liệu và phụ thuộc

- `docs/design/Settings-Market-Research.md` §2.3 (H-03, H-04, H-05), §5 (D-03, D-04, D-08), §6.
- `docs/design/mockups/settings-proposed.html` khung A.
- Phụ thuộc: `.agents/tasks/2026-11-15-settings-gate-savebar/` phải merge trước.
- `.agents/tasks/2026-11-08-rag18-confidence-gate/` — luật gate, `retrieval_debug.confidence`.
- `.agents/tasks/2026-10-27-fe06-admin-separation/` — ràng buộc bundle và hash cũ.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai trên nhánh `feat/settings-nav-retrieval-test` (commit `7e38924`). R-03, R-04,
  R-06 đã sửa trong working tree, chưa commit. `AC-01` … `AC-07` đạt; review vòng 5 `approved`
  (`self_review`).
- Blocker: không có.
- Bước tiếp theo: commit bản sửa khi người dùng yêu cầu, rồi chuyển `done`. Người dùng quyết định
  R-07/R-08 (không bắt buộc).

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-11-15T23:42:56+07:00` — `claude-agent`: tạo task từ giai đoạn 2 của tài liệu nghiên cứu; thêm D-08 (vốn ở giai
  đoạn 3) vì thuộc header bố cục mới và cùng file với task này; trạng thái `ready`, phụ thuộc task giai đoạn 1.
- `2026-11-17T21:11:00+07:00` — `claude-agent`: xác nhận `2026-11-15-settings-gate-savebar` đã merge qua PR #71; tách
  nhánh từ `dev` `08f90bb`, hoàn thành S-01 … S-05; `AC-01` … `AC-07` đạt; chuyển trạng thái `done`.
- `2026-11-17T21:13:30+07:00` — `claude-agent`: thêm dấu "—" vào dòng mô hình cho đúng câu chữ AC-03; chạy lại toàn
  bộ kiểm tra frontend, `verification.md` và `review.md` xác nhận trên `7e38924`.
- `2026-11-17T21:18:04+07:00` — `claude-agent`: review vòng 3 phát hiện R-03 (`medium`, bắt buộc;
  `AC-01` chưa đạt đầy đủ). Chuyển trạng thái `done` → `in_progress`.
- `2026-11-17T21:22:14+07:00` — `claude-agent`: sửa R-03, R-06 (chưa commit). Chromium tái hiện R-04, nên `AC-01`
  vẫn chưa đạt; giữ `in_progress`.
- `2026-11-17T21:27:01+07:00` — `claude-agent`: sửa R-04 (chưa commit); `AC-01` đạt lại, review vòng 5 `approved`.
  Chuyển `in_review`, chờ commit trước khi `done`.

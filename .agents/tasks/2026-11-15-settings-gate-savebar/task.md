# Task: Cài đặt quản trị — ngưỡng tin cậy đúng gate RAG-18 và thanh lưu theo ngữ cảnh

- ID: `2026-11-15-settings-gate-savebar`
- Trạng thái: `in_review`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("tạo task cải thiện đi", sau tài liệu nghiên cứu màn Cài đặt)
- Tạo lúc: `2026-11-15T23:42:56+07:00`
- Cập nhật lúc: `2026-11-16T00:06:27+07:00`

## Yêu cầu và kết quả mong muốn

Giai đoạn 1 của lộ trình trong `docs/design/Settings-Market-Research.md` §8: đề xuất D-01, D-02 và phần nhãn/màu của
D-05.

**Hiện trạng** (H-01, H-02, H-06, H-07 của tài liệu):

- Nhóm "Ngưỡng tương đồng & kiểm soát an toàn" ở `frontend/src/ConfigView.jsx` chưa cập nhật theo gate RAG-18:
  - Thanh "Điểm khớp từ khóa BM25 tối thiểu" ghi `guardrails.min_bm25_score`, trường mà
    `backend/app/generation/confidence.py` không còn đọc.
  - `min_bm25_norm_score` và `min_rerank_score` (đang dùng thật) không hiện.
  - Không hiện `vector_threshold_source`. Khi `min_vector_score` là `null` (model chưa hiệu chỉnh), UI hiện 0.30, giá
    trị mà backend bỏ qua.
  - Mô tả "đoạn dưới ngưỡng sẽ bị loại" sai: gate so đoạn khớp nhất rồi từ chối cả câu bằng `NO_CONTEXT_ANSWER`.
  - Mỗi lần lưu đều gửi lại mọi trường, kể cả `min_vector_score`.
  - Sau khi ghi đè ngưỡng cosine, không quay lại giá trị hiệu chỉnh được (backend bỏ qua `null`).
- Không có "Hủy thay đổi". "Mặc định" (xoá toàn bộ cấu hình đã lưu) đứng ngang nút Lưu. Không biết trường nào đã sửa.
- Nhãn lẫn Anh–Việt ("Settings", "LLM model"…). Màu teal/đen/xanh lệch hướng "Học vụ hiện đại". Thanh hệ số ứng viên
  chỉ tới 6 trong khi backend nhận 1–8. Dòng "Ngôn ngữ giao diện" tĩnh trông như một cài đặt.

**Kết quả cần có**: nhóm "Ngưỡng tin cậy" hiển thị và sửa đúng các ngưỡng gate đang dùng, có nguồn gốc ngưỡng, có cách
quay về giá trị hiệu chỉnh; form chỉ gửi trường đã đổi; thanh lưu dính đáy với Hủy/Lưu và tóm tắt thay đổi; trường đã
sửa được đánh dấu; "Khôi phục mặc định" nằm trong vùng nguy hiểm; nhãn tiếng Việt và màu thống nhất. Mockup tham
chiếu: `docs/design/mockups/settings-proposed.html` khung A (bố cục danh mục dọc và bảng thử thuộc giai đoạn 2, không
làm ở task này).

## Phạm vi

- Bao gồm:
  - Backend: `backend/app/core/config.py` (khối guardrails của `update_runtime_config`), test
    `backend/tests/test_config_api.py`, `backend/tests/test_config_persistence.py`.
  - Frontend: `frontend/src/ConfigView.jsx`, `frontend/src/lib/configDraft.js` (+ test),
    `frontend/src/SettingsView.jsx`, `frontend/src/admin/AdminShell.jsx` (nhãn), `frontend/src/models/catalog.js`
    (nhãn loại mô hình), `frontend/src/styles/config.css`, component mới cho thanh lưu nếu tách
    (`frontend/src/components/SaveBar.jsx`), test liên quan (`ConfigView.cache.test.jsx`, test mới cho ConfigView,
    `admin/AdminApp.test.jsx`, `models/ModelsView.test.jsx` nếu nhãn đổi).
- Ngoài phạm vi: bố cục danh mục dọc, đổi hash route, bảng "Thử với câu hỏi", "Lần lưu gần nhất" (task
  `2026-11-15-settings-nav-retrieval-test`); cài đặt sinh viên (task `2026-11-15-student-settings`); preset (D-07);
  đổi luật gate hoặc ngưỡng mặc định.
- Ràng buộc:
  - API `/config` giữ tương thích ngược: vẫn nhận `min_bm25_score` (client cũ, runtime config đã lưu), trường không gửi
    giữ nguyên, giá trị số của `min_vector_score`/`min_rerank_score` giữ hành vi hiện tại (quy tắc trong
    `config.py:682-695`).
  - Không thêm thư viện UI. CSS dùng token có sẵn trong `styles/tokens.css`, đúng cả sáng và tối.
  - Giữ hành vi đã có: bản nháp giữ khi đổi tab, `mergeConfigDraft` với cache dùng chung tab Mô hình, `beforeunload`,
    lưu lỗi thì giữ bản nháp và báo "CHƯA được lưu".
  - Làm trên nhánh `feat/settings-gate-savebar` tách từ `dev` đã cập nhật; commit message tiếng Anh.

## Tiêu chí nghiệm thu

- [x] AC-01: Nhóm "Ngưỡng tin cậy" không còn điều khiển cho `min_bm25_score`; có trường "Độ khớp từ khóa tối thiểu" cho
  `min_bm25_norm_score` (0–1, bước 0.01); ngưỡng cosine hiện huy hiệu theo `vector_threshold_source` (`calibrated` →
  "Đã hiệu chỉnh cho <embedding model>", `override` → "Ghi đè", `uncalibrated` → cảnh báo tín hiệu đang bị bỏ qua và
  không hiển thị 0.30); "Điểm xếp hạng lại tối thiểu" chỉ hiện khi reranker bật và provider là `cross-encoder`; khối mô
  tả nêu đúng cơ chế (so đoạn khớp nhất, trượt bất kỳ ngưỡng nào thì trả lời "Chưa tìm thấy thông tin này trong tài
  liệu." và không gọi mô hình). Có test frontend cho ba trạng thái nguồn ngưỡng và điều kiện hiện ngưỡng reranker.
- [x] AC-02: PUT `/config` từ form chỉ chứa trường khác snapshot đã lưu; lưu khi không chạm ngưỡng cosine thì payload
  không có `guardrails.min_vector_score`; payload không bao giờ chứa `min_bm25_score`. Có test frontend kiểm payload.
- [x] AC-03: Backend: `guardrails.min_vector_score: null` hoặc `guardrails.min_rerank_score: null` gửi tường minh trong PUT
  `/config` xoá ghi đè tương ứng (settings về giá trị ban đầu từ `.env`, dòng trong `app_config_overrides` bị xoá),
  response trả `vector_threshold_source` khác `override`; trường không gửi giữ nguyên; giá trị số giữ hành vi cũ. Link
  "Dùng giá trị hiệu chỉnh (<giá trị>)" trên UI gửi `null` và cập nhật form. Có test backend cho xoá ghi đè, giữ nguyên
  khi không gửi, và lưu bền qua khởi động lại (persistence).
- [x] AC-04: Khi form có thay đổi, thanh lưu dính đáy vùng nội dung hiện "<N> thay đổi chưa lưu", tóm tắt `nhãn cũ→mới`,
  nút "Hủy thay đổi" (trả form về snapshot, không gọi API) và "Lưu"; huy hiệu và nút lưu ở header panel được bỏ. Mỗi
  trường đã sửa có dấu hiệu nhìn thấy được, chữ "trước: <giá trị>" và nút trả riêng trường đó (có `aria-label`). Lưu lỗi
  vẫn giữ bản nháp; `beforeunload` vẫn hoạt động. Có test frontend cho Hủy, trả từng trường và đếm số thay đổi.
- [x] AC-05: "Khôi phục mặc định" chuyển xuống thẻ "Vùng nguy hiểm" ở cuối form, vẫn qua hộp xác nhận tông nguy hiểm
  hiện có; không còn nút này ở header.
- [x] AC-06: Nhãn và thị giác: "Settings" → "Cài đặt" (tiêu đề trang, mục sidebar admin); nhãn loại mô hình tiếng Việt
  ("Mô hình ngôn ngữ (LLM)", "Mô hình nhúng (Embedding)", "Mô hình xếp hạng lại (Reranker)"); công tắc, nút chọn số lần
  thử lại và thanh tỷ trọng dùng màu thương hiệu/trung tính thay teal/đen/xanh; bỏ viền fieldset riêng của nhóm thử lại;
  thanh hệ số ứng viên 1–8; bỏ dòng "Ngôn ngữ giao diện" tĩnh; mô tả Top-K nêu hệ quả và mặc định.
- [x] AC-07: `npm test` và `npm run build` (thư mục `frontend/`), `python -m pytest` (thư mục `backend/`) đều xanh; có ảnh
  chụp trước/sau của tab Cấu hình RAG ở 1366×820 và 390×844, sáng và tối, khi có thay đổi chưa lưu.

## Tài liệu và phụ thuộc

- `docs/design/Settings-Market-Research.md` §2.3 (H-01, H-02, H-06, H-07), §5 (D-01, D-02, D-05), §6.
- `docs/design/mockups/settings-proposed.html` khung A (hàng đã sửa, nhóm Ngưỡng tin cậy, thanh lưu).
- `.agents/tasks/2026-11-08-rag18-confidence-gate/` — hợp đồng gate, yêu cầu giữ tương thích `min_bm25_score`.
- `.agents/tasks/2026-11-15-settings-market-research/` — task nghiên cứu nguồn.
- Task sau phụ thuộc task này: `2026-11-15-settings-nav-retrieval-test` (cùng sửa `ConfigView.jsx`, `config.css`).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01 … S-05 xong trên `feat/settings-gate-savebar` (tới `415afe3`); `AC-01` … `AC-07` có bằng chứng
  `passed` trong `verification.md`; `review.md` `approved` (self_review), còn 4 nhận xét `low` hoãn lại.
- Blocker: không có.
- Bước tiếp theo: chờ người dùng đồng ý push nhánh và mở PR vào `dev`; sau khi có PR, coordinator ghi số PR và chuyển
  `done`.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-11-15T23:42:56+07:00` — `claude-agent`: tạo task từ giai đoạn 1 của tài liệu nghiên cứu theo yêu cầu người
  dùng; trạng thái `ready`. Coi yêu cầu "tạo task cải thiện" là trả lời Q-01 (làm giai đoạn 1).
- `2026-11-16T00:06:27+07:00` — `claude-agent`: triển khai xong, chuyển `in_review` (chờ push/PR). Hợp đồng `/config` bổ sung 3 trường tuỳ
  chọn trong `guardrails` (quyết định D-1, `implementation.md`).

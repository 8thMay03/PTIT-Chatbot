# Verification: 2026-11-15-confirm-bulk-pipeline-actions

- Verifier: `claude-code`.
- Trạng thái tổng: `passed` (kiểm tra tự động); kiểm tra thủ công trên trình duyệt `not_run`.
- Bản được kiểm tra: nhánh `feat/confirm-bulk-pipeline-actions`, bản commit S-01 trên `8c7c78a`.
- Môi trường: Windows 11, Node, vitest 3.2.7 (jsdom).

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-code, `2026-11-15T19:36:34+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run src/datasets/DatasetListView.test.jsx`, test `mở hộp xác nhận cho rechunk|reindex; Hủy, Esc và bấm nền không gọi API` (lần lượt đóng bằng Hủy, Esc, mousedown trên `.modal-backdrop`).
- Kỳ vọng: modal hiện; `documentsApi.rechunk` và `documentsApi.reindex` không được gọi.
- Kết quả thực tế: modal mở với đúng tiêu đề, đóng ở cả ba cách; không có POST `/ingest` hay `/ingest/chunk`.
- Trạng thái: `passed`.
- Bằng chứng: `Test Files 1 passed (1) · Tests 11 passed (11)`.

### V-02 — AC-02

- Người thực hiện / thời gian: claude-code, `2026-11-15T19:36:34+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: các test `cho chạy bảo trì toàn kho khi không còn job nền` (skipped=0), `giữ hộp xác nhận và khóa nút trong lúc nạp lại đang chạy` (skipped=2), `không chạy bảo trì nếu job nền xuất hiện ngay trước khi bấm`.
- Kỳ vọng: API được gọi đúng một lần; toast và làm mới như trước; còn job nền thì không gọi API và cảnh báo.
- Kết quả thực tế: đúng một POST `ingest/chunk`; toast "Đã chia đoạn lại 3 tài liệu · 9 đoạn."; với skipped hiện cảnh báo "Bỏ qua 2 tài liệu chưa có bản parse"; khi job nền xuất hiện thì không POST, modal đóng, hiện "Còn job parse nền đang chạy".
- Trạng thái: `passed`.
- Bằng chứng: cùng lần chạy V-01.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-code, `2026-11-15T19:36:34+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run src/DatasetView.chunkConfirm.test.jsx`.
- Kỳ vọng: hủy không gọi `datasetsApi.chunk`; xác nhận gọi đúng một lần; tiêu đề modal có tên dataset.
- Kết quả thực tế: tiêu đề "Chia đoạn lại dataset “Sổ tay”?"; Hủy/Esc/nền không POST `/datasets/ds-1/chunk`; xác nhận POST đúng một lần, toast "Đã chia đoạn lại 12 tài liệu · 41 đoạn trong “Sổ tay”."
- Trạng thái: `passed`.
- Bằng chứng: `Test Files 1 passed (1) · Tests 2 passed (2)`.

### V-04 — AC-04

- Người thực hiện / thời gian: claude-code, `2026-11-15T19:36:34+07:00`.
- Loại: review nội dung + test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: đọc diff; test `nêu phạm vi, việc nhúng lại và thời gian trong hộp xác nhận` và test V-03 kiểm tra các cụm từ.
- Kỳ vọng: đủ các ý trong AC-04, không khẳng định chi phí cụ thể.
- Kết quả thực tế: toàn kho nêu "toàn bộ 2 dataset (7 tài liệu)", "nhúng vector lại", "mất nhiều thời gian"; nạp lại thêm "parse lại file gốc" và "Markdown sửa tay được giữ nguyên"; dataset nêu "12 tài liệu trong dataset này". Không nhắc chi phí/hạn mức.
- Trạng thái: `passed`.
- Bằng chứng: lần chạy V-01, V-03. Chưa có ảnh chụp (xem mục dưới).

### V-05 — AC-05

- Người thực hiện / thời gian: claude-code, `2026-11-15T19:36:34+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: API trả promise chưa resolve; gửi Esc, mousedown nền và bấm lại nút xác nhận (cả `DatasetListView` và `DatasetView`).
- Kỳ vọng: modal không đóng; nút bị khoá.
- Kết quả thực tế: nút xác nhận và Hủy `disabled`; modal vẫn mở; chỉ một POST; resolve xong modal đóng.
- Trạng thái: `passed`.
- Bằng chứng: lần chạy V-01, V-03.

### V-06 — AC-06

- Người thực hiện / thời gian: claude-code, `2026-11-15T19:36:34+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm test`, `npm run build`.
- Kỳ vọng: cả hai pass.
- Kết quả thực tế: `Test Files 35 passed (35) · Tests 243 passed (243)`; `vite build` "✓ built in 2.23s".
- Trạng thái: `passed`.
- Bằng chứng: output lệnh trong phiên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Kiểm tra thủ công ba modal trên `/admin#documents` (giao diện sáng/tối, ảnh chụp): `not_run`. Backend và Vite đang chạy nhưng extension Claude in Chrome không kết nối. Khi kiểm tra chỉ mở modal rồi bấm Hủy; nút xác nhận sẽ chạy thật trên toàn bộ dữ liệu.

## Kết luận

- Tiêu chí đã đạt: `AC-01`..`AC-06` (bằng chứng tự động).
- Tiêu chí chưa đạt/chưa xác minh: không có; phần hiển thị thực tế trên trình duyệt chưa xem.
- Đề xuất: người yêu cầu xem nhanh ba modal trước khi merge.

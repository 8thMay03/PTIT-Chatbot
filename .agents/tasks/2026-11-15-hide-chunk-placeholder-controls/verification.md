# Verification: 2026-11-15-hide-chunk-placeholder-controls

- Verifier: `claude-code` (cùng agent triển khai).
- Trạng thái tổng: `passed` cho kiểm tra tự động; kiểm tra thủ công trên trình duyệt `not_run`.
- Bản được kiểm tra: working tree nhánh `feat/hide-chunk-placeholder-controls` trên nền `a2891b2` (cùng nội dung với commit S-01).
- Môi trường: Windows 11, Node, vitest 3.2.7, vite build.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-code, `2026-11-15T21:10:44+07:00`.
- Loại: test tự động và review mã.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run src/DocumentView.pagination.test.jsx`; grep `enabledChunks|selectedChunkIds|chunk-checkbox|chunk-type-tag|chunk-select-all|pill-switch` trong `src/DocumentView.jsx` và `src/styles/document.css`.
- Kỳ vọng: không còn switch hay checkbox trong vùng đoạn; grep không còn kết quả.
- Kết quả thực tế: test mới pass (20 thẻ, không có `[role="switch"]`, không có `input[type="checkbox"]`, không có chữ "Chọn tất cả"). Cùng test chạy trên `DocumentView.jsx` của `a2891b2` thì fail với `expected <button type="button" …> to be null`, tức test bắt đúng lỗi. Grep không có kết quả (exit 1).
- Trạng thái: `passed`.
- Bằng chứng: output vitest và grep trong phiên.

### V-02 — AC-02

- Người thực hiện / thời gian: claude-code, `2026-11-15T21:10:44+07:00`.
- Loại: test tự động; kiểm tra thủ công.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run src/DocumentView.pagination.test.jsx src/lib/chunkLocator.test.js`; review CSS `.chunk-card-top`.
- Kỳ vọng: test pass; thẻ gọn; định vị đoạn vẫn chạy.
- Kết quả thực tế: 2 file, 9 test pass (test phân trang cũ; test mới bấm thẻ → `is-hovered-target`; 7 test `chunkLocator`). CSS chỉ còn một rule `.chunk-card-top` (flex, `gap`, không `space-between`), không chừa chỗ cho điều khiển cũ. Kiểm tra trực quan rê/bấm trên trình duyệt **chưa chạy** vì extension Chrome không kết nối được.
- Trạng thái: `passed` (tự động); phần thủ công `not_run`.
- Bằng chứng: output vitest trong phiên.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-code, `2026-11-15T21:10:44+07:00`.
- Loại: review mã.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: đọc diff `DocumentView.jsx`, `document.css`.
- Kỳ vọng: đúng phương án chốt ở Q-02 (gỡ nhãn).
- Kết quả thực tế: `<span className="chunk-type-tag">Văn bản</span>` và CSS `.chunk-type-tag` đã gỡ; test V-01 xác nhận cột đoạn không còn chữ "Văn bản".
- Trạng thái: `passed`.
- Bằng chứng: diff; test V-01.

### V-04 — AC-04

- Người thực hiện / thời gian: claude-code, `2026-11-15T21:10:44+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm test`, `npm run build`.
- Kỳ vọng: cả hai pass.
- Kết quả thực tế: `npm test`: 35 file, 244 test pass. `npm run build`: `✓ built in 2.18s`.
- Trạng thái: `passed`.
- Bằng chứng: output trong phiên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Dự án không có cấu hình ESLint (`npx eslint` báo thiếu `eslint.config.*`), nên không chạy lint.
- Chưa xem trực quan thẻ đoạn trên trình duyệt (giao diện sáng/tối, rê chuột). Backend và dev server đang chạy, nhưng extension Chrome không kết nối được.

## Kết luận

- Tiêu chí đã đạt: `AC-01`, `AC-03`, `AC-04`; phần tự động của `AC-02`.
- Tiêu chí chưa đạt/chưa xác minh: phần kiểm tra thủ công của `AC-02`.
- Đề xuất: người yêu cầu mở màn chi tiết một tài liệu đã chia đoạn để xem nhanh trước khi merge.

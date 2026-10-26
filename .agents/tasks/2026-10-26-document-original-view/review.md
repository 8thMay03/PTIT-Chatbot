# Review: 2026-10-26-document-original-view

- Reviewer: `claude-code`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `dev` trên `ef97140` — `backend/app/api/routes.py`, `backend/tests/test_document_api.py`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/DocumentView.jsx`, `frontend/src/components/OriginalDocumentViewer.jsx`, `frontend/src/styles/document.css`.
- Cập nhật lúc: `2026-10-26T22:25:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-04; S-01, S-02.
- File/thay đổi cần đọc: toàn bộ diff ở trên.
- Bằng chứng kiểm chứng: V-01…V-04.
- Điểm cần đánh giá: tương thích ngược của endpoint `/file`, an toàn khi hiển thị tệp người dùng tải lên trên origin của ứng dụng, race khi đổi tài liệu, tác động tới tính năng đánh dấu đoạn, kích thước bundle.

## Nhận xét

Không có nhận xét bắt buộc. Đã đọc toàn bộ diff và đối chiếu:

- Tương thích: không truyền `inline` vẫn là `attachment` (luồng tải xuống ở `DatasetView` không đổi); `nosniff` chỉ thêm ràng buộc, kiểu nội dung đã khai báo đúng (PDF/DOCX theo đuôi tệp, MD/TXT `text/plain`).
- An toàn: tệp chỉ có thể là PDF/DOCX/MD/TXT (kiểm tra đuôi + chữ ký khi tải lên). PDF chạy trong trình xem PDF của trình duyệt, không truy cập DOM ứng dụng. MD/TXT hiển thị qua text node của React. DOCX: tắt altChunk (iframe `srcdoc` cùng origin), gỡ liên kết không an toàn sau khi render — đã kiểm chứng ở V-03. Không dùng `sandbox` cho iframe PDF vì trình xem PDF của Chrome bị chặn trong iframe sandbox.
- Race: mỗi lượt render DOCX ghi vào phần tử con mới, kết quả của lượt cũ (đã abort) chỉ ghi vào nút đã bị gỡ; `AbortController` hủy fetch khi đổi tài liệu/chế độ.
- Đánh dấu đoạn: `highlightAndScrollToChunk` tự thoát khi không có `.doc-markdown-rendered-view`, nên chế độ Bản gốc không gây lỗi; giữ Markdown làm mặc định và ghi chú trong tooltip.
- Bundle: `docx-preview` chỉ tải khi mở DOCX ở chế độ Bản gốc.

## Lịch sử các vòng review

- `2026-10-26T22:25:00+07:00` — `claude-code` — working tree trên `ef97140` — `approved`, không có R-*.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: không có.
- Phần chưa review / giới hạn: `self_review`, không phải review độc lập; chưa thử Firefox/Safari; DOCX đầu-cuối với dữ liệu thật trong kho chưa chạy (xem `verification.md`).
- Bước tiếp theo: không có; task đã `done`. Bản đã commit trùng nội dung với bản đã review (chỉ nhật ký task thay đổi sau review).

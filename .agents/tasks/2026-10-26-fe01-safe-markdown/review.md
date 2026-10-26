# Review: 2026-10-26-fe01-safe-markdown

- Reviewer: `opencode-agent`.
- Hình thức: `self_review` (chỉ có một agent trong phiên; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `feat/safe-markdown-render` (base `b24242d`) — các file
  `frontend/src/lib/markdown.js`, `frontend/src/lib/format.js`, `frontend/src/components/MarkdownView.jsx`,
  `frontend/src/ChatView.jsx`, `frontend/src/DocumentView.jsx`, CSS, `package.json`, `vite.config.js`, test.
- Cập nhật lúc: `2026-10-26T22:54:52+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: `AC-01` … `AC-06`; nhiệm vụ `S-01`, `S-02`, `S-03`.
- Bằng chứng kiểm chứng: `verification.md` mục V-01 … V-10, gồm 38 test pass, build production,
  so cấu trúc 330 bảng D26 và 2 ảnh before/after byte-identical.
- Điểm cần đánh giá: đúng đắn bảo mật (allowlist, escape, link scheme), đúng phạm vi, khả năng bảo trì,
  tương thích giao diện cũ, hạn chế hiệu năng/bundle.

## Nhận xét

### R-01 — Raw HTML table được bọc bằng thay chuỗi trước sanitize

- Vị trí: `frontend/src/lib/markdown.js:60-79` (`wrapRawHtmlTables`).
- Liên quan: `AC-01`, `AC-04`, `S-01`.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `resolved`.
- Vấn đề và tác động: `html_block` của bảng HTML thô được thêm `div.doc-table-wrapper` bằng
  `String.replace` trước DOMPurify. Nếu attribute chứa chuỗi `</table>` thì wrapper có thể chèn sai chỗ
  trong markup, nhưng nội dung vẫn bị DOMPurify xử lý sau đó. Không tạo được thẻ/thuộc tính thực thi.
- Đề nghị xử lý: giữ cách này nhưng phải có test bảng HTML thô và test XSS; đã có.
- Người xử lý: `opencode-agent`.
- Phản hồi/cách sửa: không đổi code; bổ sung test “thẻ HTML thô trong bảng cũng bị lọc thuộc tính” và
  test bảng HTML có `onclick`/`onmouseover`/`iframe`.
- Bằng chứng sau sửa: V-01, V-04; 330/330 bảng D26 có wrapper và `doc-table`, 0 phần tử chứa `on*`/URL nguy hiểm.
- Xác nhận của reviewer: đã đọc hook `afterSanitizeAttributes`, allowlist và chạy test — `resolved`.

### R-02 — Render toàn văn D26 tốn ~1,1–1,5 giây

- Vị trí: `frontend/src/lib/markdown.js:293-297`, `frontend/src/components/MarkdownView.jsx`.
- Liên quan: `AC-06`, phi chức năng.
- Mức độ: `medium`.
- Bắt buộc sửa: không (không nằm trong tiêu chí nghiệm thu; chất lượng hiển thị/bảo mật đã đạt).
- Trạng thái: `deferred`.
- Vấn đề và tác động: DOMPurify xử lý ~812k ký tự mất khoảng 1 giây; lần mở tài liệu lớn đầu tiên có thể
  làm UI khựng ngắn. Đã đo trong jsdom, chưa đo trên trình duyệt thật.
- Đề nghị xử lý: `MarkdownView` đã memo theo `content`/`sources`, nên chỉ trả giá một lần cho mỗi tài liệu;
  nếu cần cải thiện nữa thì virtualize/lazy render toàn văn hoặc chuyển sanitize sang worker.
- Người xử lý: chưa cần trong task này.
- Nếu deferred: lý do là ngoài phạm vi và không chặn tiêu chí; hướng theo dõi là mở task tối ưu hiệu năng
  khi màn tài liệu có thêm yêu cầu.
- Xác nhận của reviewer: `deferred`, coordinator (kiêm nhiệm) đồng ý.

### R-03 — `breaks: true` thay đổi cách gom đoạn so với bản cũ

- Vị trí: `frontend/src/lib/markdown.js:15-22`.
- Liên quan: `AC-03`, `AC-04`.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `resolved`.
- Vấn đề và tác động: bản cũ tạo một `<p>` cho mỗi dòng; markdown-it gom các dòng liền nhau vào một `<p>`
  với `<br>`, nên số phần tử `p` và phạm vi highlight một đoạn có thể khác đôi chút.
- Đề nghị xử lý: chọn `breaks: true` để giữ xuống dòng của PDF/DOCX (nếu `false`, các dòng bị nối bằng dấu cách,
  sai nội dung tài liệu); kiểm tra lại selector highlight vẫn khớp.
- Người xử lý: `opencode-agent`.
- Phản hồi/cách sửa: đã đối chiếu `DocumentView` selectors (`.doc-p`, `.doc-h1`…`.doc-h6`, `li`, `tr`,
  `.doc-table-wrapper`) — không đổi; 38 test và so bảng pass.
- Bằng chứng sau sửa: V-03, V-04, V-07.
- Xác nhận của reviewer: chấp nhận; `resolved`.

### R-04 — Bundle chính tăng 132,60 kB (53,46 kB gzip)

- Vị trí: `frontend/package.json`, bundle `assets/index-*.js`.
- Liên quan: `AC-06`.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: thêm `markdown-it` + `dompurify` làm bundle chính tăng từ 279,15 kB lên 411,75 kB.
  Với ứng dụng nội bộ, mức tăng này chấp nhận được; nếu cần giảm có thể lazy-load renderer hoặc thay bằng
  thư viện nhỏ hơn.
- Đề nghị xử lý: ghi nhận số liệu; không đổi trong task này vì yêu cầu ưu tiên thư viện chuẩn + DOMPurify.
- Người xử lý: chưa cần.
- Nếu deferred: lý do là đánh đổi có chủ đích, đã ghi trong `verification.md`; theo dõi nếu có yêu cầu
  ngân sách bundle.
- Xác nhận của reviewer: `deferred`.

## Lịch sử các vòng review

- `2026-10-26T22:54:52+07:00` — `opencode-agent` — working tree FE-01 — `approved` (self_review);
  R-01/R-03 resolved, R-02/R-04 deferred không bắt buộc.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc cần xử lý: không.
- Nhận xét hoãn lại: R-02 (hiệu năng toàn văn), R-04 (kích thước bundle).
- Phần chưa review / giới hạn: không chạy E2E trên ứng dụng thật; ảnh D26 chụp từ HTML hai parser + CSS
  production thay vì màn hình ứng dụng đang chạy. Đã ghi rõ trong `verification.md`.
- Bước tiếp theo: người dùng xem diff và commit/merge nhánh `feat/safe-markdown-render` khi đồng ý.

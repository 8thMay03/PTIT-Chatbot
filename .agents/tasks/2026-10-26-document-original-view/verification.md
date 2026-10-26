# Verification: 2026-10-26-document-original-view

- Verifier: `claude-code`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `dev` trên `ef97140` + diff của task (chưa commit).
- Môi trường: Windows 11; backend `.venv` Python (FastAPI 0.162.0, Starlette 1.10.0); Docker Compose (backend uvicorn `--reload`, frontend Vite dev server hot reload); Node 24 (build cục bộ), Node 20 trong container; Chrome qua Claude in Chrome.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: `claude-code` / `2026-10-26T22:21:00+07:00`.
- Loại: test tự động + kiểm tra thủ công.
- Thư mục chạy: `backend/`; repo root.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q tests/test_document_api.py`; `curl -D -` tới `http://localhost:8000/api/documents/<id>/file?inline=true`, không `inline`, qua proxy Vite `:5173`, tài liệu `.md`, id không tồn tại.
- Kỳ vọng: inline → `inline` + `nosniff`; mặc định → `attachment`; MD → `text/plain; charset=utf-8`; id sai → 404.
- Kết quả thực tế: 18 passed. `Opus-5.5-Effort-Levels.pdf`: `content-type: application/pdf`, `content-disposition: inline; filename="Opus-5.5-Effort-Levels.pdf"`, `x-content-type-options: nosniff`; không `inline` → `attachment; ...`; tên tệp Unicode qua proxy Vite → `inline; filename*=utf-8''S%E1%BB%95%20tay...pdf`; `.md` → `text/plain; charset=utf-8`; id `nope` → `{"detail":"Không tìm thấy tài liệu."}`.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra pytest và curl trong phiên.

### V-02 — AC-02

- Người thực hiện / thời gian: `claude-code` / `2026-10-26T22:22:00+07:00`.
- Loại: kiểm tra thủ công trên dev server (`http://localhost:5173`, Chrome).
- Thư mục chạy: không áp dụng.
- Lệnh / thao tác: Dataset → mở `Opus-5.5-Effort-Levels.pdf` → bấm "Bản gốc"; quay lại, mở tài liệu `.md`; reload trang và mở lại.
- Kỳ vọng: mặc định Markdown; "Bản gốc" hiển thị PDF trong trình xem PDF; lựa chọn được ghi nhớ.
- Kết quả thực tế: mặc định "Markdown" active. Sau khi bấm "Bản gốc", cột trái hiển thị trình xem PDF của Chrome (thanh công cụ, 1/3 trang, các trang đồ họa gốc). Mở tài liệu khác và sau reload vẫn là "Bản gốc" (`localStorage.ptit_doc_view_mode = "original"`). Có một lần trạng thái về Markdown ngay sau khi Vite báo `optimized dependencies changed. reloading` (lần đầu phát hiện dependency `docx-preview`); các lần thử lại sau đó đều giữ đúng. Nút mở tab mới trỏ tới `/api/documents/<id>/file?inline=true`. Không có lỗi console.
- Trạng thái: `passed`.
- Bằng chứng: ảnh chụp màn hình trong phiên (PDF ở chế độ Bản gốc), kết quả `javascript_tool`.

### V-03 — AC-03

- Người thực hiện / thời gian: `claude-code` / `2026-10-26T22:24:00+07:00`.
- Loại: kiểm tra thủ công trên dev server.
- Thư mục chạy: không áp dụng.
- Lệnh / thao tác:
  - MD: mở `Sổ tay sinh viên D26 _1_ _1_.md` ở chế độ Bản gốc.
  - DOCX: kho chưa có tài liệu DOCX nào được nạp, nên tạm sao chép `data/raw/Quy trình cấp giấy tờ tại VP1C.docx` thành `frontend/tmp-docx-test.docx` (Vite phục vụ) và ghi đè `window.fetch` trong trang: chi tiết tài liệu MD trả `file_type: "docx"`, `/file?inline=true` trả tệp DOCX đó. Lặp lại với DOCX tự tạo (python-docx) chứa liên kết `javascript:alert(document.domain)` và `https://ptit.edu.vn/` (không bấm vào liên kết).
  - Lỗi: ghi đè `/file?inline=true` trả 404 `{"detail": "File nguồn không còn trên đĩa."}`.
  - Đã xóa cả hai tệp tạm, xóa khóa `localStorage` đã tạo khi thử và đóng tab.
- Kỳ vọng: MD thô; DOCX thành trang vừa cột; liên kết nguy hiểm bị vô hiệu; lỗi hiện state-block kèm tải xuống.
- Kết quả thực tế: MD hiển thị nguồn thô (`# HỌC VIỆN CÔNG NGHỆ...`, `*Hành trình mới...*`). DOCX render 1 trang, đúng tiếng Việt, đậm/nghiêng/danh sách; `zoom = 0.842` cho cột rộng 714px; không hiện nút mở tab mới (DOCX). Liên kết: `LINK-JS` → `href = null`; `LINK-HTTPS` → `href="https://ptit.edu.vn/"`, `target="_blank"`, `rel="noopener noreferrer"`; 0 iframe trong khung DOCX. Lỗi: "Không mở được bản gốc / File nguồn không còn trên đĩa. / Thử tải xuống" (sau khi sửa, `text-decoration: none`). Không có lỗi console sau reload.
- Trạng thái: `passed`.
- Bằng chứng: ảnh chụp màn hình DOCX và trạng thái lỗi trong phiên, kết quả `javascript_tool`.

### V-04 — AC-04

- Người thực hiện / thời gian: `claude-code` / `2026-10-26T22:25:00+07:00`.
- Loại: test tự động + build.
- Thư mục chạy: `backend/`, `frontend/`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q tests`; `npm run build`.
- Kỳ vọng: pass.
- Kết quả thực tế: `365 passed, 1 skipped` (skip có sẵn: `test_chunker_tables_benchmark.py:146` thiếu tệp benchmark thật trong `data/`). Build pass; `docx-preview` tách thành chunk riêng `docx-preview-*.js` 174 KB (51 KB gzip), bundle chính 279 KB.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra lệnh trong phiên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Nút "Thử tải xuống" bị gạch chân (thẻ `<a>` dùng lớp `ghost-btn`) → thêm lớp `doc-original-download` với `text-decoration: none`; kiểm tra lại: `none`.
- Chưa xác minh: DOCX đầu-cuối với tài liệu DOCX thật đã nạp vào kho (V-03 dùng tệp DOCX thật nhưng phản hồi API giả lập; phía backend endpoint không phụ thuộc định dạng và đã kiểm tra với PDF/MD). Chưa kiểm tra trên Firefox/Safari (CSS `zoom` cần Firefox ≥ 126).

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-02, AC-03, AC-04.
- Tiêu chí chưa đạt/chưa xác minh: không có (giới hạn ở mục trên).
- Đề xuất: bàn giao người dùng thử. Mã đã commit (`049c903` + commit frontend kế tiếp) trùng với bản đã kiểm tra.

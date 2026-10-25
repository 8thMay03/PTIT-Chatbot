# Verification: 2026-10-25-upload-parser-selection

- Verifier: `claude-code`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `dev` trên `b27f320` + thay đổi S-01, S-02.
- Môi trường: Windows 11, backend `.venv` (Python), Node/Vite; Docker compose dev (backend hot reload, frontend mount `./frontend`), `.env` bật LlamaParse.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-code / `2026-10-25T14:00:25+07:00`.
- Loại: test tự động + gọi API thủ công.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `test_parser_options_by_file_name_before_upload`; `curl "http://localhost:8000/api/parsers?file_name=a.pdf"`.
- Kỳ vọng: docling (mặc định) + llamaparse; đuôi lạ → `[]`; thiếu tham số → 422.
- Kết quả thực tế: test pass; curl trả `{"parsers":[{"name":"docling","is_default":true},{"name":"llamaparse","is_default":false}]}`.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra test và curl ở trên.

### V-02 — AC-02

- Người thực hiện / thời gian: claude-code / `2026-10-25T14:00:25+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `test_upload_document_passes_selected_parser` (route truyền `parser_name`, lỗi → 422); `test_upload_parses_with_selected_parser_and_stores_it` (pipeline thật, LlamaParse mock: `metadata.parser = "llamaparse"`, chunk chứa nội dung LlamaParse, Docling không chạy; `.md` + `llamaparse` → `DocumentParseError` "không hỗ trợ").
- Kỳ vọng: cả hai pass.
- Kết quả thực tế: pass.
- Trạng thái: `passed`.
- Bằng chứng: V-04.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-code / `2026-10-25T14:00:25+07:00`.
- Loại: kiểm tra thủ công trên Chrome (http://localhost:5173, màn Dataset).
- Lệnh / thao tác: giả lập kéo-thả 2 tệp (`Quy che dao tao.pdf`, `ghi-chu.md`) bằng `DragEvent("drop")`; chọn LlamaParse; bấm Hủy.
- Kỳ vọng: modal "Chọn parser cho tài liệu tải lên", Docling chọn sẵn, ghi chú 1 tệp dùng parser mặc định; Hủy đóng modal, không tải lên.
- Kết quả thực tế: đúng như kỳ vọng; sau Hủy danh sách vẫn 2 tài liệu, không có POST tải lên.
- Trạng thái: `passed`.
- Bằng chứng: ảnh chụp màn hình modal trong phiên làm việc.

### V-04 — AC-04

- Người thực hiện / thời gian: claude-code / `2026-10-25T14:00:25+07:00`.
- Loại: test tự động + build.
- Thư mục chạy: `backend`, `frontend`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q tests`; `npm run build`.
- Kỳ vọng: pass.
- Kết quả thực tế: `350 passed, 1 skipped` (trước thay đổi 347 passed / 1 skipped); build Vite thành công.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra lệnh trong phiên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Chưa chạy: xác nhận tải lên thật bằng LlamaParse (gửi file lên LlamaCloud, tốn credit). Luồng backend tương ứng đã có test với SDK mock.
- Chưa chạy: trường hợp tắt LlamaParse trên UI (không mở modal) — suy ra từ logic `choosable.length === 0`, chưa kiểm thủ công.

## Kết luận

- Tiêu chí đã đạt: AC-01…AC-04.
- Tiêu chí chưa đạt/chưa xác minh: không có (xem mục chưa chạy).
- Đề xuất: người dùng thử tải lên thật một PDF nhỏ bằng LlamaParse.

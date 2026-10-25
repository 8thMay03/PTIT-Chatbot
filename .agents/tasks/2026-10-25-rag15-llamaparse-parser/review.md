# Review: 2026-10-25-rag15-llamaparse-parser

- Reviewer: `claude-code`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `in_progress`.
- Bản được review: working tree nhánh `feat/rag15-llamaparse-parser` trên nền `af2d2b7` (`dev`) (chưa commit) — vòng 1 phủ S-01…S-05, S-07 và script đo của S-06.
- Cập nhật lúc: `2026-10-25T12:15:34+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-08; S-01…S-07.
- File/thay đổi cần đọc: `git diff` của `backend/app/{api/routes.py,core/config.py,db/repositories.py,ingestion/*.py,parsers/__init__.py}`, file mới `backend/app/parsers/llamaparse.py`, tests, `frontend/src/components/ParserSelectionModal.jsx`, `pyproject.toml`, `Dockerfile`, `.env.example`, `README.md`, `documents/rag-eval/rag-15/experiments/*.py`.
- Bằng chứng kiểm chứng: V-01…V-06 (`passed` phần tự động), V-07 phần Docling, V-08 mức mã.
- Điểm cần đánh giá: Docling không đổi hành vi và vẫn mặc định; lỗi/timeout/retry; không lộ API key; cache không đọc nhầm giữa parser/cấu hình; fallback parser; test không phụ thuộc mạng/SDK; xung đột RAG-06.

## Nhận xét

### R-01 — Timeout request của SDK quá ngắn cho file lớn

- Vị trí: `backend/app/parsers/llamaparse.py` `_parse_remote` (khởi tạo `LlamaCloud`).
- Liên quan: AC-02, S-02.
- Mức độ: `high`.
- Bắt buộc sửa: có.
- Trạng thái: `resolved`.
- Vấn đề và tác động: SDK mặc định timeout request 60 giây; upload PDF D26 37 MB qua mạng chậm sẽ timeout ở bước upload dù `LLAMAPARSE_TIMEOUT_SECONDS=900` (giá trị này chỉ áp cho vòng poll).
- Đề nghị xử lý: truyền cùng timeout cho client.
- Người xử lý: `claude-code`.
- Phản hồi/cách sửa: thêm `timeout=timeout` vào `LlamaCloud(...)`; test kiểm `clients[0]["timeout"]`.
- Bằng chứng sau sửa: `test_parse_sends_options_and_joins_pages_in_order`; suite 347 passed (V-05).
- Xác nhận của reviewer: đã đọc lại diff, đạt.

### R-02 — Trang lỗi lẻ bị bỏ qua chỉ với cảnh báo log

- Vị trí: `llamaparse.py` `_markdown_from_result`.
- Liên quan: AC-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open`.
- Vấn đề và tác động: nếu LlamaParse trả lỗi cho một số trang, nội dung các trang đó vắng mặt trong index; người quản trị chỉ thấy qua log. Đổi lại, một trang lỗi không chặn cả sổ tay 268 trang (và không mất credit đã dùng).
- Đề nghị xử lý: S-06 ghi số trang lỗi thực tế; nếu khác 0, cân nhắc đưa số trang lỗi vào response parse/metadata ở task sau.
- Người xử lý: `claude-code`.

### R-03 — Modal chọn sẵn parser mặc định, không phải parser tài liệu đang dùng

- Vị trí: `frontend/src/components/ParserSelectionModal.jsx` (khởi tạo `selected` theo `is_default`).
- Liên quan: AC-04, AC-06.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open`.
- Vấn đề và tác động: sau khi parse bằng LlamaParse, mở lại modal vẫn chọn sẵn Docling; người dùng dễ bấm xác nhận và parse lại bằng Docling. Danh sách tài liệu cũng chưa hiển thị parser đang dùng (`metadata.parser` chưa có trong `serialize_document`).
- Đề nghị xử lý: thêm `parser` vào `DocumentItem` và chọn sẵn parser hiện tại trong modal — ngoài phạm vi S-05 (chỉ thêm mô tả), đề xuất cho task frontend.
- Người xử lý: coordinator quyết định (đề xuất `deferred`).

### R-04 — Parse LlamaParse đồng bộ trong request HTTP

- Vị trí: `POST /api/documents/{id}/parse` (không đổi trong task này).
- Liên quan: S-06, FE-07.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open`.
- Vấn đề và tác động: sổ tay 268 trang có thể mất vài phút; proxy/nginx có timeout ngắn sẽ cắt request dù backend vẫn chạy xong (kết quả vẫn được cache). Đã có trong phạm vi FE-03/FE-07.
- Đề nghị xử lý: S-06 ghi thời gian thực tế để FE-07 tham khảo.
- Người xử lý: `claude-code` (ghi số liệu).

## Lịch sử các vòng review

- `2026-10-25T12:15:34+07:00` — `claude-code` — working tree (S-01…S-05, S-07, script S-06) — R-01 `high` đã sửa và xác nhận; R-02…R-04 `low`, không bắt buộc. Chưa kết luận vì S-06 chưa xong.

## Kết luận

- Kết luận: `pending`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: đề xuất hoãn R-03 sang task frontend (chờ coordinator/người dùng).
- Phần chưa review / giới hạn: kết quả chạy LlamaParse thật và báo cáo `rag-15/README.md` (S-06).
- Bước tiếp theo: hoàn tất S-06 → review vòng 2 phần báo cáo và log thật → kết luận.

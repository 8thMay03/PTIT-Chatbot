# Task: Tách ingest thành hai bước parse và chunk, cho phép sửa Markdown bằng tay

- ID: `2026-10-26-split-parse-chunk`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: người dùng (phiên Claude Code 2026-10-26: "nên tách ingest ra làm 2 bước: parse và chunk chứ không nên gộp vào như bây giờ"; bổ sung: "thêm 1 màn hình cho phép sửa file markdown bằng tay trong trường hợp parse bị lỗi, màn này cho phép xem file raw md và file md đã được render để đối chiếu trực tiếp")
- Tạo lúc: `2026-10-26T23:36:15+07:00`
- Cập nhật lúc: `2026-10-27T00:01:20+07:00`

## Yêu cầu và kết quả mong muốn

Hiện trạng (nhánh `dev`, `1a59682`): mọi lối vào (`POST /documents`, `POST /documents/{id}/parse`, `POST /ingest`) chạy liền parse → chuẩn hóa → chunk → embed → ghi DB trong một lời gọi.

- Markdown đã parse không được lưu chính thức: chỉ có cache Docling/LlamaParse theo hash file (DB không tham chiếu), parser `text` không lưu bản nào; mất cache thì tab Markdown ghép lại từ chunk (lặp đoạn chồng lấn).
- Không có thao tác "chỉ chia đoạn lại" khi đổi cấu hình chunk/normalizer.
- Lỗi embedding khi tải lên làm mất cả kết quả parse (phải tải lên lại).
- `status` luôn `active`; không xem/sửa được Markdown trước khi chia đoạn.

Kết quả cần có:

1. Bước **parse**: parser + chuẩn hóa → lưu Markdown vào `documents.parsed_text`; trạng thái `parsed`. Chunk cũ (nếu có) vẫn phục vụ truy xuất cho tới khi chia đoạn lại.
2. Bước **chunk**: đọc `parsed_text` → chia đoạn → embed → thay toàn bộ chunk của tài liệu; trạng thái `active`.
3. Tải lên **chỉ parse** và dừng ở `parsed` (quyết định của người dùng).
4. Màn **sửa Markdown**: soạn Markdown thô và xem bản render cạnh nhau; lưu ghi `parsed_text`, chuyển `parsed` để chia đoạn lại.

## Phạm vi

- Bao gồm: `backend/app/db/models.py`, `backend/alembic/versions/0004_*.py`, `backend/app/db/repositories.py`, `backend/app/ingestion/{pipeline.py,loaders.py}`, `backend/app/api/{routes.py,schemas.py}`, `backend/scripts/ingest.py`, test backend liên quan; `frontend/src/{DatasetView.jsx,DocumentView.jsx}`, `frontend/src/components/{ParserSelectionModal.jsx,MarkdownEditorView.jsx}`, CSS liên quan; `README.md`.
- Ngoài phạm vi: job nền/hàng đợi (vẫn chạy đồng bộ), lịch sử phiên bản Markdown, sửa nội dung từng chunk, đổi parser/chunker.
- Ràng buộc: `POST /ingest` (Nạp lại toàn bộ) giữ ngữ nghĩa parse + chunk nguyên tử như cũ; tài liệu cũ chưa có `parsed_text` vẫn xem/chat được; migration Alembic khớp model (`alembic check`).

## Tiêu chí nghiệm thu

- [x] AC-01: Migration thêm `documents.parsed_text`, `documents.parsed_at`; `alembic upgrade head` + `check` + `downgrade base` chạy được.
- [x] AC-02: `POST /documents` và `POST /documents/{id}/parse` chỉ parse: lưu `parsed_text`, `status=parsed`, không gọi embedding, không đổi chunk hiện có; parse lại ra cùng nội dung với tài liệu `active` thì giữ `active`.
- [x] AC-03: `POST /documents/{id}/chunk` chia đoạn + embed từ `parsed_text`, thay chunk nguyên tử, `status=active`; 404 khi không có tài liệu; 409 khi chưa có bản parse hoặc bản parse đổi trong lúc chia đoạn.
- [x] AC-04: `POST /ingest/chunk` chia đoạn lại mọi tài liệu có `parsed_text` mà không gọi parser; trả số tài liệu, số đoạn, số tài liệu bỏ qua.
- [x] AC-05: `GET/PUT /documents/{id}/markdown` đọc/ghi Markdown (PUT trả bản Markdown kèm `content_hash` mới); PUT đánh dấu sửa tay, chuyển `parsed` khi nội dung đổi, 409 khi `base_hash` lệch, 422 khi rỗng. Nạp lại toàn bộ và `--stage parse` giữ bản sửa tay; parse lại đơn lẻ ghi đè và xóa dấu sửa tay.
- [x] AC-06: `python -m scripts.ingest --stage all|parse|chunk` hoạt động; mặc định `all` như cũ.
- [x] AC-07: Giao diện: badge trạng thái (Đã nạp / Chờ chia đoạn / Cần chia đoạn lại), nút Chia đoạn từng tài liệu và Chia đoạn lại toàn bộ; màn sửa Markdown hai cột (thô / render) có Lưu, Hủy, cảnh báo khi rời trang chưa lưu; modal parse lại cảnh báo khi tài liệu đã sửa tay.
- [x] AC-08: Toàn bộ `backend/tests` pass; `npm run build` và test frontend pass.

## Tài liệu và phụ thuộc

- Task `2026-10-25-upload-parser-selection`, `2026-10-25-rag15-llamaparse-parser` (parser lưu trong `metadata.parser`).
- Task `2026-10-26-fe01-safe-markdown` (`MarkdownView` render an toàn, dùng lại cho cột render).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01…S-03 xong trên working tree nhánh `feat/split-parse-chunk` (tách từ `dev` tại `1a59682`), đã commit `55806ad` (backend) và `966599d` (frontend), cộng một commit README + task; chưa push. AC-01…AC-08 có bằng chứng (backend 383 passed / 1 skipped, frontend build + 43 test pass, kiểm tra UI trên dev server); self_review `approved`, R-01/R-02 (low) deferred. DB Postgres dev đã lên revision `0004_document_parsed_text`.
- Blocker: không có.
- Bước tiếp theo: người dùng thử Chia đoạn trên UI (gọi embedding OpenAI, chưa chạy) và quyết định push/PR vào `dev`; coordinator chuyển `done` sau đó.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-26T23:36:15+07:00` — `claude-code`: người dùng chọn (1) tải lên dừng ở `parsed`, người dùng tự bấm Chia đoạn; (2) Markdown đã parse lưu ở cột DB `documents.parsed_text`. Embedding thuộc bước chunk. `POST /ingest` giữ parse + chunk nguyên tử (thao tác dựng lại kho, không để kho nửa vời).
- `2026-10-26T23:36:15+07:00` — `claude-code`: người dùng bổ sung màn sửa Markdown bằng tay (thô + render đối chiếu); gộp vào task vì dựa trực tiếp trên `parsed_text`. Quyết định mặc định: Lưu không tự chia đoạn; Nạp lại toàn bộ giữ bản sửa tay; parse lại đơn lẻ ghi đè có cảnh báo; PUT dùng `base_hash` chống ghi đè lẫn nhau.
- `2026-10-26T23:55:47+07:00` — `claude-code`: `PUT /documents/{id}/markdown` trả `DocumentMarkdown` (có `content_hash` mới) thay vì `DocumentItem` để trình sửa lưu nhiều lần vẫn kiểm tra xung đột; `parsed_text` đặt `deferred`. Chuyển `in_review`.
- `2026-10-27T00:01:20+07:00` — `claude-code`: người dùng yêu cầu commit; commit `55806ad` (backend), `966599d` (frontend) và commit README + task trên `feat/split-parse-chunk`. Giữ `in_review` chờ thử Chia đoạn thật và PR.

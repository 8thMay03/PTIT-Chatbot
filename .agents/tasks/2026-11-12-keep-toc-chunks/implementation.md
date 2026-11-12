# Implementation: 2026-11-12-keep-toc-chunks

## Tổng quan triển khai

Nhánh `feat/keep-toc-chunks` (tách từ `dev` tại `92aa804`). S-01, S-02, S-03 đã xong; index local D26 đã chunk lại (1010 → 1017 chunk).

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-11-12T23:20:00+07:00`.
- Đã làm: trong `_drop_noise_lines`, section "MỤC LỤC" không còn bị bỏ:
  - giữ dòng heading "MỤC LỤC";
  - bảng mục lục (`_is_toc_like_table`) được giữ; bảng Markdown 2 cột có dòng phân cách và hàng đầu kết thúc bằng số trang được thêm header `|Mục|Trang|` + `|-|-|` (`_with_toc_table_header`). Lý do: LlamaParse đặt entry đầu ("Lời nói đầu|3") vào vị trí header, chunker lặp header ở mọi phần bảng; với header chung, hai bảng mục lục ngắt trang của D26 được `_merge_page_break_tables` ghép thành một bảng logic;
  - entry dạng chấm dẫn hoặc số trang đậm được viết lại thành `… (trang N)` (`_normalize_toc_entry`); `_TOC_LINE_LIKE` nhận thêm dạng `(trang N)` để cleaner idempotent;
  - sửa lỗi có sẵn: dòng `**…** **24**` sau `strip("*")` mất dấu hiệu số trang đậm và kết thúc section sớm → kiểm tra `_TOC_LINE_LIKE` trên cả `title`;
  - entry mục lục lạc ngoài section "MỤC LỤC" vẫn bị lọc (luật `_is_noise_line` không đổi).
  - thêm `is_toc_heading(heading)` công khai.
- File thay đổi: `backend/app/ingestion/cleaner.py`, `backend/tests/test_chunker.py` (đổi 7 test "drops" thành "keeps/rewrites", thêm 4 test: header thật giữ nguyên, bảng ngắt trang dùng header chung, số trang đậm chỉ viết lại trong section, idempotent).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: thay AC-03 (phần mục lục) của RAG-06 và vế "bảng mục lục D26 vẫn bị lọc" của AC-06 table-chunking-coverage.
- Kiểm tra đã chạy: xem V-01, V-05.
- Còn lại/blocker: không có.

### S-02 — claude-code

- Cập nhật lúc: `2026-11-12T23:20:00+07:00`.
- Đã làm: `_chunk_records` ghi `"is_toc": is_toc_heading(chunk.heading)` vào metadata mọi chunk. Chưa có bên đọc; để dành cho việc hạ trọng số/lọc nếu cần.
- File thay đổi: `backend/app/ingestion/pipeline.py`, `backend/tests/test_document_pipeline.py` (+1 test), `backend/scripts/check_chunks.py` (docstring), `backend/tests/test_rag_testset_300.py` (comment lỗi thời).
- Kiểm tra đã chạy: V-02.
- Còn lại/blocker: không có.

### S-03 — claude-code

- Cập nhật lúc: `2026-11-12T23:20:00+07:00`.
- Đã làm: đo baseline bm25/hybrid trên `ptit_ragas_100` (index cũ, fingerprint `d33ac7329944`); chunk lại tài liệu `e0997dd2…` bằng `ingestion_pipeline.chunk_document` (embed lại qua OpenAI `text-embedding-3-small`); đo lại trên `ptit_ragas_100` và `ptit_rag_300` (index mới, fingerprint `a43f1dd48c7f`).
- File thay đổi: `documents/rag-eval/keep-toc/{before,after}_{bm25,hybrid}.json`, `after_rag300_{bm25,hybrid}.json`, `README.md`.
- Ghi chú: lần chạy đầu truyền `--output ../documents/...` nên script ghi ra `D:\GithubRepositories\documents\rag-eval\keep-toc` (ngoài repo, script resolve theo repo root); đã chuyển hai file vào đúng chỗ và xóa thư mục `keep-toc` rỗng do mình tạo. Thư mục `D:\GithubRepositories\documents\rag-eval\rag-06` có sẵn từ trước, không đụng tới.
- Còn lại/blocker: không có baseline `ptit_rag_300` trên index cũ (index đã thay khi nghĩ tới) → chỉ phân tích mục lục chen top-4 trên bản sau.

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

### HANDOFF-claude-code-001 — S-01…S-03

- Từ / đến: `claude-code` / người dùng.
- Đã hoàn tất: S-01, S-02, S-03.
- File/branch/commit/patch: nhánh `feat/keep-toc-chunks`, PR #59 (https://github.com/8thMay03/PTIT-Chatbot/pull/59); commit xem `git log`. Thay đổi file PDF trong `data/` (xóa ở `data/`, thêm ở `data/raw/`) là của người dùng, không nằm trong commit.
- Kiểm chứng: `verification.md` V-01…V-05 đạt.
- Review: `review.md` self_review `approved`, không có R-* bắt buộc.
- Hạn chế / còn lại: container `backend` mount `./backend/app`, `./backend/scripts` và chạy `uvicorn --reload`, nên đã chạy code mới (log WatchFiles reload, `is_toc_heading` có trong container) — không cần build lại image. Container chạy theo nhánh đang checkout: về `dev` trước khi merge thì chunk lại sẽ bỏ mục lục.
- Bước tiếp theo: review và merge PR #59 vào `dev`.
- Phản hồi nhận bàn giao: <chờ người dùng>.

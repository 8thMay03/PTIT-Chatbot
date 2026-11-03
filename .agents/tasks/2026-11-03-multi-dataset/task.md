# Task: Chia kho tài liệu thành nhiều dataset và thiết kế lại trang Dataset của admin

- ID: `2026-11-03-multi-dataset`
- Trạng thái: `in_progress`
- Coordinator: `claude-code`
- Người yêu cầu: `user`
- Tạo lúc: `2026-11-03T22:14:26+07:00`
- Cập nhật lúc: `2026-11-04T04:10:00+07:00`

## Yêu cầu và kết quả mong muốn

Hiện trạng (đã đọc mã tại `dev@f07e845`):

- Trang Dataset của admin (`frontend/src/DatasetView.jsx`, 1090 dòng) chỉ là **một bảng phẳng** gồm mọi tài liệu. Không có khái niệm nhóm/bộ dữ liệu.
- DB không có bảng dataset: `documents` (`backend/app/db/models.py`) không có cột nhóm; `id = sha256(source_path)` và ID chunk dạng `<source_path>::chunk-N` (`backend/app/ingestion/pipeline.py`).
- File nguồn tải lên được ghi phẳng vào `DOCUMENTS_PATH/<tên file>` (`pipeline.parse_staged_upload`), nên hai tài liệu cùng tên luôn ghi đè nhau.
- Retrieval quét **toàn bộ** chunk: `PgVectorStore.search` và `BM25Search._load_chunks` không có bộ lọc nào.
- Nút “Bật/Tắt” từng tài liệu chỉ là state trong phiên, không ảnh hưởng chatbot (`DatasetView.jsx:78-80`).

Kết quả cần có:

1. Admin tạo, đổi tên/mô tả, bật/tắt và xóa được **nhiều dataset**; mỗi tài liệu thuộc đúng một dataset.
2. Trang Dataset thành hai cấp: **danh sách dataset** (thẻ có thống kê) → **tài liệu trong một dataset** (bảng hiện tại, giới hạn trong dataset đó).
3. Tải tài liệu lên vào một dataset cụ thể; chuyển tài liệu đã có sang dataset khác mà không phải parse/nhúng lại.
4. Bật/tắt dataset có tác dụng thật: chatbot chỉ truy xuất chunk thuộc dataset đang bật.
5. Thao tác chia đoạn lại/parse lại theo phạm vi một dataset; các thao tác toàn kho vẫn còn.
6. Toàn bộ tài liệu hiện có được đưa vào dataset “Mặc định” khi nâng cấp, không mất dữ liệu.

## Phạm vi

- Bao gồm:
  - Backend: model + migration `datasets`, repository, API dataset, lọc theo dataset ở upload/list/retrieval, chuyển tài liệu, xóa dataset, chia đoạn/parse theo dataset.
  - Ingestion: thư mục lưu file theo dataset, cách sinh ID tài liệu/chunk không phụ thuộc đường dẫn, giữ dataset khi “Nạp lại toàn bộ”.
  - Frontend admin: route `#documents` / `#documents/<datasetId>`, trang danh sách dataset, trang tài liệu của dataset, các hộp thoại tạo/sửa/xóa/chuyển.
  - Test backend/frontend cho phần trên.
- Ngoài phạm vi:
  - Cho sinh viên chọn dataset khi hỏi ở trang chat (retriever nhận `dataset_ids` để làm sau, xem D-03).
  - Cấu hình parser/chunk/embedding riêng cho từng dataset (D-05).
  - Một tài liệu thuộc nhiều dataset (D-01).
  - Lưu tiêu đề tài liệu lên server, phân quyền nhiều admin.
- Ràng buộc:
  - Migration không làm mất tài liệu/chunk/embedding; không di chuyển file cũ trên đĩa.
  - Khi mọi dataset đang bật, kết quả retrieval phải giống trước (baseline `documents/rag-eval/`).
  - API cũ giữ tương thích: `GET /api/documents` không tham số vẫn trả mọi tài liệu; `POST /api/documents` không có `dataset_id` → dataset mặc định.
  - Route mới gắn `require_admin` (test quét route trong `backend/tests/test_admin_auth.py`).
  - Link `/admin#documents` đã lưu vẫn mở được trang Dataset.
  - Không ghi secret/.env vào nhật ký.

## Tiêu chí nghiệm thu

- [ ] AC-01: Có bảng `datasets` và cột `documents.dataset_id` (NOT NULL, có index). Migration `0008` chạy được trên DB đang có dữ liệu (mọi tài liệu thuộc dataset `default` tên “Mặc định”), kể cả khi `init_db()` đã tạo bảng `datasets` trước; `downgrade` khôi phục schema cũ. Trên SQLite (test) dataset mặc định được tạo tự động.
- [ ] AC-02: API dataset: liệt kê kèm thống kê (số tài liệu, số đoạn, số tài liệu chờ chia đoạn, dung lượng), tạo, xem, sửa (tên/mô tả/bật-tắt), xóa. Tên 1–100 ký tự sau khi trim, không trùng (không phân biệt hoa/thường) → 409; dataset không tồn tại → 404; không xóa được dataset mặc định → 409; xóa dataset có job parse đang chạy → 409; xóa dataset xóa luôn tài liệu, chunk và file nguồn của nó.
- [ ] AC-03: Tải lên vào dataset chỉ định ghi file ở `DOCUMENTS_PATH/datasets/<dataset_id>/<tên>`. Cùng tên file ở hai dataset khác nhau cùng tồn tại, không ghi đè nhau; cùng tên trong cùng dataset vẫn thay thế bản cũ như hiện nay. `GET /api/documents?dataset_id=` chỉ trả tài liệu của dataset đó; `DocumentItem` và `ParseJobItem` có `dataset_id`.
- [ ] AC-04: Chuyển một hoặc nhiều tài liệu sang dataset khác: giữ nguyên `id` tài liệu, chunk và embedding (không gọi embedding model), file nguồn đi theo sang thư mục dataset đích; trùng tên file ở đích → 409 và không đổi gì; liên kết `message_sources` không bị mất.
- [ ] AC-05: Chunk của dataset đang tắt không xuất hiện trong vector search, BM25, `/api/retrieval/test` và câu trả lời chat; bật lại có hiệu lực ngay, không cần nạp lại. Khi mọi dataset bật, `scripts.eval_retrieval` (bm25/vector/hybrid) cho kết quả trùng baseline.
- [ ] AC-06: Chia đoạn lại toàn bộ một dataset và parse lại toàn bộ một dataset (job nền, bỏ qua tài liệu có Markdown sửa tay như “Nạp lại toàn bộ”). “Nạp lại toàn bộ” và “Chia đoạn lại toàn bộ” vẫn hoạt động và giữ nguyên dataset + `id` của từng tài liệu.
- [ ] AC-07: Trang danh sách dataset: thẻ dataset (tên, mô tả, thống kê, trạng thái bật/tắt, cảnh báo chờ chia đoạn), tìm kiếm, tạo/sửa/xóa (xóa phải gõ lại tên dataset, hiển thị số tài liệu/đoạn bị xóa), bật/tắt; có trạng thái đang tải, rỗng, lỗi; cảnh báo khi không còn dataset nào bật. Hiển thị đúng ở 360/768/1280px, sáng và tối.
- [ ] AC-08: Trang tài liệu của dataset: breadcrumb “Dataset / <tên>”, header thống kê, mọi thao tác hiện có (parse, chia đoạn, sửa Markdown, xem, tải gốc/Markdown, xóa, job nền, kéo thả) chỉ trong dataset đó; tải lên vào dataset đang mở; thao tác hàng loạt “Chuyển sang dataset…”. Deep link `#documents/<datasetId>` mở đúng dataset, dataset không tồn tại → quay về danh sách kèm thông báo; nút Back của trình duyệt từ trang dataset về danh sách.
- [ ] AC-09: `pytest` backend và `npm test` + `npm run build` frontend đều pass, có test mới cho AC-01…AC-08 theo `plan.md`.

## Tài liệu và phụ thuộc

- Mã liên quan: `frontend/src/DatasetView.jsx`, `frontend/src/DocumentView.jsx`, `frontend/src/admin/AdminShell.jsx`, `frontend/src/lib/appRoute.js`, `frontend/src/api/documents.js`, `frontend/src/api/queryClient.js`, `frontend/src/styles/dataset.css`; `backend/app/db/models.py`, `backend/app/db/repositories.py`, `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/app/ingestion/{pipeline,uploads,jobs,loaders}.py`, `backend/app/retrieval/{bm25,retriever}.py`, `backend/app/vectordb/{base,pgvector_store}.py`, `backend/app/generation/rag_chain.py`.
- Task liên quan: `2026-10-26-split-parse-chunk`, `2026-10-27-background-parse-jobs`, `2026-10-27-fe06-admin-separation`, `2026-10-24-rag-eval-retrieval-baseline`, `2026-10-30-rag-ui-market-research` (mục “Chọn phạm vi nguồn”).
- Baseline retrieval: `documents/rag-eval/README.md`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai S-01…S-08 trên nhánh `feat/multi-dataset` (chưa commit); S-09 đang kiểm chứng — tự động pass, còn thiếu thủ công UI + eval baseline.
- Blocker: review vòng 3 `blocked` — R-08…R-16 đã `resolved`; còn R-06 (kiểm tra thủ công UI + ảnh) và R-07 (eval baseline, cần Postgres có dữ liệu + embedding key).
- Bước tiếp theo: verifier chạy V-05/V-07/V-08 và lưu `evidence/`; reviewer xác nhận R-06/R-07.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-03T22:14:26+07:00 — claude-code: tạo task ở trạng thái `draft`, viết kế hoạch S-01…S-09 và các quyết định cần xác nhận D-01…D-07.
- 2026-11-03T22:23:20+07:00 — claude-code: người dùng duyệt task (“duyệt task”), chấp nhận toàn bộ phương án đề xuất D-01…D-07; chuyển `ready` → `in_progress`, tạo nhánh `feat/multi-dataset`.
- 2026-11-04T04:10:00+07:00 — claude-code: triển khai xong S-01…S-08 (backend + frontend + README, chưa commit); S-09 tự động pass, còn thiếu thủ công UI + eval baseline (xem `verification.md`, `review.md` R-06/R-07).
- 2026-11-03T23:03:45+07:00 — claude-code (reviewer): review vòng 2 `changes_requested`, thêm R-08…R-19 (xem `review.md`). Task giữ `in_progress`.
- 2026-11-03T23:49:00+07:00 — claude-code (reviewer): review vòng 3 xác nhận R-08…R-16 `resolved`, review `blocked` chờ bằng chứng R-06/R-07. Task giữ `in_progress`.

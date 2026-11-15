# Implementation: 2026-11-15-confirm-bulk-pipeline-actions

## Tổng quan triển khai

Nhánh `feat/confirm-bulk-pipeline-actions` (tách từ `dev` tại `8c7c78a`). Ba thao tác hàng loạt giờ mở `Modal` xác nhận trước khi gọi API; logic sau xác nhận giữ nguyên.

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-11-15T11:08:18+07:00` — chưa giao.
- Cập nhật lúc: `2026-11-15T19:36:34+07:00` — đã triển khai, chuyển `in_review`.
- Đã làm:
  - `frontend/src/datasets/DatasetListView.jsx`: thêm state `pendingMaintenance` (`"rechunk"` | `"reindex"` | `null`). Mục menu gọi `requestMaintenance(kind)` (đóng menu, mở modal). Nút xác nhận gọi `runMaintenance()`; thứ tự cũ giữ nguyên: đặt `maintBusy` → `fetchActiveParseJobs()` → nếu còn job nền thì đóng modal và hiện cảnh báo như cũ → gọi API → toast → `refresh()`. Modal đóng trong `finally`. `closeMaintenanceConfirm` bỏ qua khi `maintBusy` nên Esc/nền/Hủy không đóng lúc đang chạy; Hủy và nút xác nhận bị khoá.
  - Nội dung: nêu phạm vi "mọi tài liệu của toàn bộ N dataset (M tài liệu), kể cả dataset đang tắt" (M là tổng `document_count`, chỉ hiện khi mọi dataset có số), việc nhúng vector lại và thời gian chạy. "Nạp lại toàn bộ" thêm ý parse lại file gốc và giữ nguyên Markdown sửa tay; dùng `tone="danger"`. Nếu job nền xuất hiện trong lúc modal mở, nút xác nhận bị khoá và modal hiện dòng `role="status"` giải thích.
  - `frontend/src/DatasetView.jsx`: nút "Chia đoạn lại dataset" mở modal `confirmChunkAll` (cùng mẫu `confirmParseAll`), tiêu đề có tên dataset, mô tả có số tài liệu (`dataset.document_count`, dự phòng `documents.length`). Xác nhận gọi `chunkDataset` như cũ; modal đóng trong `finally`.
  - Đã đối chiếu backend: `/ingest/chunk` và `/ingest` xử lý tài liệu của mọi dataset, không lọc theo `enabled` (`backend/app/ingestion/pipeline.py`: `chunk_documents`, `build_chunks`), nên câu "kể cả dataset đang tắt" đúng.
- File thay đổi: `frontend/src/datasets/DatasetListView.jsx`, `frontend/src/DatasetView.jsx`, `frontend/src/datasets/DatasetListView.test.jsx`, `frontend/src/DatasetView.chunkConfirm.test.jsx` (mới).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: không đổi API; chỉ dùng lại `Modal`.
- Kiểm tra đã chạy: xem `verification.md` (vitest 243/243, build pass).
- Còn lại/blocker: chưa kiểm tra thủ công trên trình duyệt vì extension Claude in Chrome không kết nối, nên chưa có ảnh chụp ba modal. Không chạy thao tác thật (rechunk/reindex) trên dữ liệu.
- Ghi nhận ngoài phạm vi: khi `/ingest` (nạp lại) trả `skipped`, toast vẫn ghi "Đã chia đoạn lại …" (hành vi có sẵn, giữ nguyên theo ràng buộc của task).

## Trao đổi giữa agents

Chưa có thông báo.

## Bàn giao

- Từ claude-code tới người yêu cầu (`2026-11-15T19:36:34+07:00`): S-01 xong trên nhánh `feat/confirm-bulk-pipeline-actions`. Việc cần làm: xem ba modal trên `/admin#documents` (chỉ mở rồi bấm Hủy), push nhánh, mở PR vào `dev`.

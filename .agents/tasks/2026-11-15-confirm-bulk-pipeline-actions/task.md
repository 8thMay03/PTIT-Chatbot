# Task: Thao tác chia đoạn và nạp lại hàng loạt chạy ngay, không hỏi xác nhận

- ID: `2026-11-15-confirm-bulk-pipeline-actions`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-15T11:08:18+07:00`
- Cập nhật lúc: `2026-11-15T19:36:34+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: rà soát giao diện frontend ngày 2026-11-15 (lỗi số 6). Phát hiện khi đọc mã; màn quản trị chưa chạy được vì backend tắt.

Hành vi hiện tại (đối chiếu trên `dev` @ `0fdd444`):

- `frontend/src/datasets/DatasetListView.jsx:135-160`, menu "Bảo trì":
  - "Chia đoạn lại toàn bộ" gọi `runMaintenance("rechunk")` → `documentsApi.rechunk()` (dòng 79): chia đoạn và nhúng vector lại mọi tài liệu của mọi dataset.
  - "Nạp lại toàn bộ" gọi `runMaintenance("reindex")` → `documentsApi.reindex()`: parse lại mọi file gốc rồi chia đoạn và nhúng vector.
  - Cả hai chạy ngay khi bấm. Giải thích phạm vi chỉ nằm trong thuộc tính `title`, không hiện trên thiết bị cảm ứng và dễ bị bỏ qua.
- `frontend/src/DatasetView.jsx:612-621`: nút "Chia đoạn lại dataset" gọi thẳng `chunkDataset` (dòng 379). Trong khi đó nút "Parse lại dataset" ngay bên cạnh (dòng 623-632) mở modal xác nhận (dòng 1066 trở đi).

Tác động: bấm nhầm là chạy lại cả pipeline. Việc này mất thời gian, có thể tốn hạn mức của parser hoặc nhà cung cấp embedding tuỳ cấu hình, và kết quả tìm kiếm có thể thay đổi trong lúc chạy.

Kết quả cần có: cả ba thao tác mở hộp xác nhận (`frontend/src/components/Modal.jsx`) trước khi gọi API. Hộp xác nhận nêu phạm vi, hệ quả và có nút xác nhận ghi rõ hành động.

## Phạm vi

- Bao gồm: `frontend/src/datasets/DatasetListView.jsx`, `frontend/src/DatasetView.jsx`, test (`datasets/DatasetListView.test.jsx`, `DatasetView.parseJobs.test.jsx` hoặc test mới).
- Ngoài phạm vi: đổi API backend; chuyển rechunk sang job nền; thêm tiến trình chi tiết.
- Ràng buộc: giữ nguyên logic hiện có sau khi xác nhận (kiểm tra job parse nền đang chạy, toast kết quả, làm mới danh sách). Câu chữ không khẳng định chi phí cụ thể khi chưa biết parser và embedding đang dùng.

## Tiêu chí nghiệm thu

- [x] AC-01: Bấm "Chia đoạn lại toàn bộ" hoặc "Nạp lại toàn bộ" mở modal xác nhận. Bấm "Hủy", nhấn Esc hoặc bấm nền thì không gọi `documentsApi.rechunk` hay `documentsApi.reindex` (vitest).
- [x] AC-02: Bấm nút xác nhận mới gọi API; hành vi sau đó (kiểm tra job parse nền, toast, làm mới) như trước khi sửa (vitest).
- [x] AC-03: "Chia đoạn lại dataset" mở modal xác nhận có tên dataset; hủy thì không gọi `datasetsApi.chunk`, xác nhận thì gọi (vitest).
- [x] AC-04: Nội dung modal nêu: phạm vi (toàn bộ dataset hoặc một dataset, kèm số tài liệu nếu có sẵn trong dữ liệu đang hiển thị); việc nhúng lại vector; với "Nạp lại toàn bộ", file gốc được parse lại và Markdown sửa tay được giữ nguyên; thao tác có thể mất nhiều thời gian.
- [x] AC-05: Trong lúc thao tác đang chạy, nút xác nhận bị khoá và modal không đóng bằng Esc hoặc bấm nền (giống modal "Parse lại dataset").
- [x] AC-06: `npm test` và `npm run build` pass.

## Tài liệu và phụ thuộc

- Code: `frontend/src/datasets/DatasetListView.jsx` (`runMaintenance`, menu "Bảo trì"), `frontend/src/DatasetView.jsx` (`chunkDataset`, modal `confirmParseAll`), `frontend/src/components/Modal.jsx`.
- Không có task khác cùng sửa các file này.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01 đã triển khai trên `feat/confirm-bulk-pipeline-actions`; vitest và build pass; self_review `approved`. Chưa kiểm tra thủ công trên trình duyệt (extension Chrome không kết nối).
- Blocker: không có.
- Bước tiếp theo: người yêu cầu xem ba modal trên `/admin#documents` (chỉ mở rồi Hủy), rồi review/merge PR #66 (https://github.com/8thMay03/PTIT-Chatbot/pull/66) vào `dev`; đóng task `done` sau khi merge.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-15T11:08:18+07:00 — claude-code: tạo task `draft` từ kết quả rà soát giao diện ngày 2026-11-15 theo yêu cầu "với mỗi lỗi hãy tạo 1 task".
- 2026-11-15T19:36:34+07:00 — claude-code: người yêu cầu giao triển khai ("implement"); claude-code nhận S-01, verifier và reviewer (`self_review`). Chuyển `in_review` sau khi vitest/build pass.

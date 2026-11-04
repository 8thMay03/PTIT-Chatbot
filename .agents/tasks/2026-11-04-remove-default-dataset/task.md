# Task: Loại bỏ dataset mặc định

- ID: `2026-11-04-remove-default-dataset`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-04T23:23:40+07:00`
- Cập nhật lúc: `2026-11-04T23:23:40+07:00`

## Yêu cầu và kết quả mong muốn

Sau multi-dataset (`2026-11-03-multi-dataset`, quyết định D-06), hệ thống có dataset đặc biệt id `default` (“Mặc định”): tự tạo trong `init_db()`, không xóa được, luôn xếp đầu và là nơi rơi vào khi upload/parse không ghi `dataset_id`. Người dùng yêu cầu loại bỏ dataset mặc định khỏi hệ thống: mọi dataset đều bình thường, mọi tài liệu phải thuộc một dataset do admin chọn rõ ràng.

Quyết định đã chốt với người dùng (2026-11-04):

- Dòng `default` đang có trong DB **giữ lại như dataset thường** (đổi tên/tắt/xóa được, không còn ưu tiên). Không migration dữ liệu.
- Nạp lại toàn kho gặp file chưa thuộc dataset nào (không có trong DB và không nằm dưới `datasets/<id>/` của dataset đang tồn tại) → **bỏ qua và ghi log**.

## Phạm vi

- Bao gồm: `backend/app/db/`, `backend/app/api/` (routes, schemas), `backend/app/ingestion/` (pipeline, jobs), `backend/scripts/check_chunks.py`, test backend liên quan, `frontend/src/api/datasets.js`, `frontend/src/datasets/` (DatasetCard, DatasetListView), README.
- Ngoài phạm vi: migration xóa/đổi id dòng `default` cũ; cho sinh viên chọn dataset khi chat.
- Ràng buộc: DB hiện có vẫn chạy được không cần migration; tài liệu đã có trong DB giữ dataset khi nạp lại.

## Tiêu chí nghiệm thu

- [x] AC-01: `init_db()` trên DB trống không tạo dataset nào; `GET /api/datasets` trả `[]`.
- [x] AC-02: Mọi dataset (kể cả dòng `default` cũ) đổi tên/tắt/xóa được qua API và UI.
- [x] AC-03: `POST /api/documents` thiếu `dataset_id` → 422; dataset không tồn tại → 404.
- [x] AC-04: Rebuild/parse toàn kho bỏ qua file chưa thuộc dataset và ghi log; tài liệu đã có trong DB giữ dataset cũ.
- [x] AC-05: Không còn tham chiếu `DEFAULT_DATASET_ID`/`ensure_default_dataset`/`is_default` (của dataset) trong mã.

## Tài liệu và phụ thuộc

- `.agents/tasks/2026-11-03-multi-dataset` (D-06 bị thay thế bởi task này).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai và kiểm chứng tự động trên nhánh `feat/remove-default-dataset`; chưa commit; chưa chạy thử app thật.
- Blocker: không có.
- Bước tiếp theo: người dùng xem diff, commit/PR; chạy thử UI với DB thật nếu cần (V-06).

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-04T23:23:40+07:00 — claude-code: tạo task, chốt hai quyết định trên với người dùng; thay D-06 của multi-dataset.

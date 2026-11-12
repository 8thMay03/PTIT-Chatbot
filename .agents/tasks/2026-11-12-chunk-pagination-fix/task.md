# Task: Sửa nút chuyển trang danh sách đoạn trong màn xem tài liệu

- ID: `2026-11-12-chunk-pagination-fix`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: người dùng (8thMay03)
- Tạo lúc: `2026-11-12T23:28:08+07:00`
- Cập nhật lúc: `2026-11-12T23:28:08+07:00`

## Yêu cầu và kết quả mong muốn

Trong màn xem chunk của một tài liệu (`DocumentView`), bấm "Trang sau" không chuyển trang: badge nhảy sang 2 rồi bị kéo về 1. Cần bấm trang sau/trước chuyển đúng trang và giữ nguyên trang đó.

Nguyên nhân:
1. Khi đổi trang, query key mới chưa có dữ liệu → `total = 0` → `totalPages = 1`; effect kẹp trang đặt `page` về 1 ngay lập tức.
2. Effect debounce tìm kiếm chạy 350ms sau khi mở màn dù ô tìm kiếm rỗng và gọi `setPage(1)`, nên lần bấm chuyển trang trong khoảng đó cũng bị reset.

## Phạm vi

- Bao gồm: `frontend/src/DocumentView.jsx`, test mới `frontend/src/DocumentView.pagination.test.jsx`.
- Ngoài phạm vi: API backend, giao diện phân trang, chế độ tìm kiếm.
- Ràng buộc: nhánh `feat/chunk-pagination-fix` tách từ `dev`. Nhánh cũ `feat/fix-chunk-pagination` (commit `eb10627`, chưa merge, message tiếng Việt) chỉ sửa nguyên nhân 1 nên không dùng lại.

## Tiêu chí nghiệm thu

- [x] AC-01: Từ trang 1 bấm "Trang sau" hai lần lần lượt hiện `2 / 3` và `3 / 3` với dữ liệu đúng offset (tài liệu 45 đoạn, 20 đoạn/trang).
- [x] AC-02: Bộ test frontend và `vite build` không hồi quy.

## Tài liệu và phụ thuộc

- Không có.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã sửa và kiểm chứng bằng test tự động; chưa commit, chưa kiểm tra thủ công trên trình duyệt.
- Blocker: không có.
- Bước tiếp theo: người dùng xác nhận trên trình duyệt; commit và mở PR vào `dev`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-12T23:28:08+07:00 — claude-code: tạo task, sửa cả hai nguyên nhân, chuyển `in_review`.

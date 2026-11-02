# Review: 2026-11-02-download-markdown

- Reviewer: `opencode`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: working tree branch `feat/download-markdown` (diff `-w` 124 insertions: `backend/app/api/routes.py`, `frontend/src/api/documents.js`, `frontend/src/DatasetView.jsx`, `frontend/src/DocumentView.jsx`).
- Cập nhật lúc: `2026-11-02T10:35:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 (endpoint download Markdown), AC-02 (UI dataset + chi tiết), AC-03 (không vỡ cũ); nhiệm vụ S-01/S-02.
- File/thay đổi cần đọc: diff `-w` toàn bộ 4 file trên.
- Bằng chứng kiểm chứng: `verification.md` V-01 (25 passed + script 200/404/409 + admin scan 2 passed), V-02 (build pass + 168 frontend tests), V-03 (hồi quy).
- Điểm cần đánh giá: tính đúng đắn (nội dung/headers/mã lỗi), tương thích (giữ tải gốc), bảo mật (`require_admin`, filename sanitize, `nosniff`), khả năng bảo trì.

## Nhận xét

### R-01 — Chưa có test backend vĩnh viễn cho endpoint mới

- Vị trí: `backend/tests/test_document_api.py` (thiếu case `/markdown/download`).
- Liên quan: AC-01.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open`.
- Vấn đề và tác động: endpoint mới chỉ được kiểm chứng bằng script tạm (TestClient mock) trong V-01, chưa có case cố định trong suite nên hồi quy sau này phụ thuộc kiểm tra tay.
- Đề nghị xử lý: follow-up thêm 1 test (200/404/409 + header) vào `test_document_api.py` khi chạm tiếp vào khu vực documents.
- Người xử lý: `opencode (follow-up)`.
- Phản hồi/cách sửa: ghi nhận deferred; không chặn merge vì V-01 đã cover hành vi và `test_document_api.py` hiện tại vẫn pass.
- Bằng chứng sau sửa: chưa áp dụng.
- Xác nhận của reviewer: giữ `open` dạng deferred có lý do.
- Nếu deferred: đồng ý deferred — endpoint nhỏ, đã kiểm chứng thủ công đầy đủ; bổ sung test ở task tiếp theo.

## Lịch sử các vòng review

- 2026-11-02T10:35:00+07:00 — opencode — bản working tree `feat/download-markdown` — self_review, 1 nhận xét low (deferred), kết luận approved.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01 (bổ sung test vĩnh viễn ở follow-up).
- Phần chưa review / giới hạn: chưa E2E trình duyệt với backend thật + dữ liệu thật (đã nêu trong verification).
- Bước tiếp theo: coordinator đóng task, commit branch `feat/download-markdown` để merge vào `dev`.

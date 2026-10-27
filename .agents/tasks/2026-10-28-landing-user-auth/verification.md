# Verification: 2026-10-28-landing-user-auth

- Verifier: `claude-agent`.
- Trạng thái tổng: `not_run`.
- Bản được kiểm tra: chưa có (chưa triển khai).
- Môi trường: <ghi khi chạy: OS, Python, Node, trình duyệt>.

## Kiểm chứng tiêu chí

Mọi mục dưới chưa chạy. Verifier điền khi có bản tích hợp.

### V-01 — AC-01 (trang landing)

- Người thực hiện / thời gian: chưa chạy.
- Loại: test component + kiểm tra thủ công trên trình duyệt.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm test -- LandingPage`; mở `/` ở 360/768/1280 px, chủ đề sáng và tối, duyệt bằng
  Tab; trạng thái chưa và đã đăng nhập.
- Kỳ vọng: đủ các khối theo AC-01, không cuộn ngang, landmark + một `h1`, CTA đúng trạng thái.
- Kết quả thực tế: chưa chạy.
- Trạng thái: `not_run`.
- Bằng chứng: <ảnh chụp, đầu ra test>.

### V-02 — AC-02 (đăng ký)

- Người thực hiện / thời gian: chưa chạy.
- Loại: test tự động backend.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_user_auth.py`.
- Kỳ vọng: `201`/`409`/`422`/`503` đúng trường hợp; hash scrypt có salt, không chứa mật khẩu gốc.
- Kết quả thực tế: chưa chạy.
- Trạng thái: `not_run`.
- Bằng chứng: <đầu ra pytest>.

### V-03 — AC-03 (đăng nhập, đăng xuất, phiên, không leo thang admin)

- Người thực hiện / thời gian: chưa chạy.
- Loại: test tự động backend.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_user_auth.py tests/test_admin_auth.py`.
- Kỳ vọng: `401` cùng thông điệp cho sai mật khẩu/email không tồn tại; `429` không khoá client khác; cookie
  hỏng → chưa đăng nhập; cookie người dùng gọi route admin → `401`.
- Kết quả thực tế: chưa chạy.
- Trạng thái: `not_run`.
- Bằng chứng: <đầu ra pytest>.

### V-04 — AC-04 (hội thoại theo tài khoản)

- Người thực hiện / thời gian: chưa chạy.
- Loại: test tự động backend + kiểm tra thủ công hai trình duyệt.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_user_conversations.py tests/test_conversation_sessions.py`; thủ
  công: chat ẩn danh → đăng ký → thấy hội thoại cũ; đăng nhập cùng tài khoản ở trình duyệt khác.
- Kỳ vọng: theo AC-04.
- Kết quả thực tế: chưa chạy.
- Trạng thái: `not_run`.
- Bằng chứng: <đầu ra pytest, mô tả quan sát>.

### V-05 — AC-05 (luồng frontend)

- Người thực hiện / thời gian: chưa chạy.
- Loại: test component + kiểm tra thủ công.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm test`; thủ công: đăng ký, đăng nhập với `next` hợp lệ/không hợp lệ, lỗi từng
  mã, đăng xuất, link cũ `/#documents`, `/#settings/appearance`.
- Kỳ vọng: theo AC-05.
- Kết quả thực tế: chưa chạy.
- Trạng thái: `not_run`.
- Bằng chứng: <đầu ra test, mô tả quan sát>.

### V-06 — AC-06 (bundle)

- Người thực hiện / thời gian: chưa chạy.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm run build` (với `BUNDLE_REPORT=1` nếu script yêu cầu) rồi `npm run check:bundle`.
- Kỳ vọng: JS ban đầu landing/auth không chứa module chat/admin; chat không chứa admin và không vượt mức
  FE-06. Ghi số gzip từng trang.
- Kết quả thực tế: chưa chạy.
- Trạng thái: `not_run`.
- Bằng chứng: <đầu ra script>.

### V-07 — AC-07 (tài liệu)

- Người thực hiện / thời gian: chưa chạy.
- Loại: review tài liệu.
- Thư mục chạy: gốc repo.
- Lệnh / thao tác: đối chiếu `README.md`, `.env.example` với `config.py` và route thực tế.
- Kỳ vọng: đủ biến và route theo AC-07, khớp mã.
- Kết quả thực tế: chưa chạy.
- Trạng thái: `not_run`.
- Bằng chứng: <tham chiếu dòng>.

### V-08 — AC-08 (bộ kiểm tra đầy đủ)

- Người thực hiện / thời gian: chưa chạy.
- Loại: test tự động.
- Thư mục chạy: `backend/`, `frontend/`.
- Lệnh / thao tác: `pytest`; `npm test`; `npm run build`; `npm run check:bundle`.
- Kỳ vọng: tất cả thành công.
- Kết quả thực tế: chưa chạy.
- Trạng thái: `not_run`.
- Bằng chứng: <số test thực tế, đầu ra>.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Chưa có. Toàn bộ V-01 … V-08 `not_run` vì chưa triển khai.

## Kết luận

- Tiêu chí đã đạt: chưa có.
- Tiêu chí chưa đạt/chưa xác minh: AC-01 … AC-08 (chưa triển khai).
- Đề xuất: triển khai theo `plan.md` sau khi task chuyển `ready`.

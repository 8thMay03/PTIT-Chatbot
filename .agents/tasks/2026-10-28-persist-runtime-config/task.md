# Task: Lưu cấu hình admin vào Postgres, mã hoá API key

- ID: `2026-10-28-persist-runtime-config`
- Trạng thái: `in_review`
- Coordinator: `claude-agent`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-10-28T22:19:30+07:00`
- Cập nhật lúc: `2026-10-28T22:40:00+07:00`

## Yêu cầu và kết quả mong muốn

Hiện tại `PUT /api/config` chỉ đổi đối tượng `settings` trong RAM (`update_runtime_config`), nên mọi
cấu hình admin chỉnh trên UI (LLM, retrieval, reranker, guardrails) mất khi backend restart. Màn
Cấu hình RAG còn báo "Đã lưu cấu hình RAG lên máy chủ" khiến người dùng tưởng đã lưu bền.

Kết quả cần có: cấu hình admin đổi trên UI được lưu vào Postgres và áp lại khi khởi động. Người yêu
cầu chốt: **API key / mật khẩu lưu trong Postgres phải được mã hoá**.

## Phạm vi

- Bao gồm: bảng + migration lưu override, mã hoá secret, PUT/reset/GET `/api/config`, nạp lúc khởi
  động, thông báo trên màn Mô hình, `.env.example`, test backend.
- Ngoài phạm vi: lưu embedding (model nạp lúc khởi động, quyết định số chiều vector — vẫn chỉ đổi
  qua `.env`); đồng bộ cấu hình giữa nhiều worker/instance khi đang chạy; nhật ký ai sửa (admin dùng
  chung một mật khẩu).
- Ràng buộc: cấu hình bảo mật (`ADMIN_PASSWORD`, session secret, `LLM_BASE_URL_ALLOWLIST`,
  `DATABASE_URL`, `CONFIG_ENCRYPTION_KEY`...) không bao giờ lấy từ DB; không ghi secret vào log.

## Tiêu chí nghiệm thu

- [x] AC-01: Thay đổi qua `PUT /api/config` được ghi vào DB và áp lại sau khi backend khởi động lại;
  chỉ lưu phần khác `.env`, đổi về đúng giá trị `.env` thì xoá; reset xoá toàn bộ.
- [x] AC-02: API key chỉ lưu dạng bản mã (Fernet, khoá `CONFIG_ENCRYPTION_KEY` trong env); bản rõ
  không xuất hiện trong DB. Thiếu/sai khoá thì từ chối lưu API key (422), không đổi gì; trường
  thường vẫn lưu được. Hỗ trợ xoay khoá.
- [x] AC-03: Lỗi DB khi lưu trả 503 và cấu hình đang chạy giữ nguyên như trước request; khởi động
  không sập khi DB lỗi hoặc dòng hỏng (secret không giải mã được, URL ngoài allowlist, trường ngoài
  whitelist bị bỏ qua).
- [x] AC-04: Chỉ whitelist trường RAG/LLM được lưu; trường bảo mật không bao giờ đọc từ DB.
- [x] AC-05: UI màn Mô hình báo đúng hành vi lưu và cảnh báo khi máy chủ thiếu khoá mã hoá.
- [x] AC-06: Không hồi quy test backend hiện có.

## Tài liệu và phụ thuộc

- `.agents/tasks/2026-10-27-fe06-admin-separation/` (allowlist URL, `require_admin`).
- Dependency mới: `cryptography>=42.0.0` (cần build lại image backend).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai, kiểm chứng và commit (`4f362c3`); self-review approved. Chờ merge vào `dev`.
- Blocker: không có.
- Bước tiếp theo: người dùng thêm `CONFIG_ENCRYPTION_KEY` vào `.env`, merge `4f362c3` vào `dev`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-10-28T22:19:30+07:00 — claude-agent: người dùng chọn lưu cấu hình vào Postgres, yêu cầu mã
  hoá API key/mật khẩu. Chọn Fernet + khoá trong env; thiếu khoá thì từ chối lưu secret (fail closed)
  thay vì lưu bản rõ. Không lưu embedding (cần re-index).

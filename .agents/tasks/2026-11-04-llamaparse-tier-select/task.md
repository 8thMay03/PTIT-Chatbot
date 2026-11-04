# Task: Chọn tier khi parse bằng LlamaParse

- ID: `2026-11-04-llamaparse-tier-select`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-04T22:54:52+07:00`
- Cập nhật lúc: `2026-11-04T22:54:52+07:00`

## Yêu cầu và kết quả mong muốn

Khi chọn parser LlamaParse (upload hoặc parse lại), admin chọn được một trong bốn tier `fast | cost_effective | agentic | agentic_plus`. Trước đây tier chỉ đặt cố định qua `LLAMAPARSE_TIER`.

## Phạm vi

- Bao gồm: `backend/app/parsers/` (registry, LlamaParse), modal chọn parser và luồng upload trong `frontend/src`, test liên quan, README.
- Ngoài phạm vi: đổi API endpoint/schema; cấu hình tier cho parser khác.
- Ràng buộc: tài liệu đã lưu `parser = "llamaparse"` vẫn chạy như cũ (theo `LLAMAPARSE_TIER`, cùng cache).

## Tiêu chí nghiệm thu

- [x] AC-01: Backend nhận `parser_name = "llamaparse:<tier>"`, gọi LlamaCloud với đúng tier, cache theo tier, lưu nguyên giá trị vào metadata tài liệu; tier không hợp lệ bị từ chối; `llamaparse` không kèm tier giữ hành vi cũ.
- [x] AC-02: `GET /api/parsers` và `/documents/{id}/parsers` trả `variants` + `default_variant` cho LlamaParse.
- [x] AC-03: Modal chọn parser hiển thị 4 tier (credit/trang) khi chọn LlamaParse, mặc định là `default_variant`, xác nhận gửi `llamaparse:<tier>`; upload nhiều tệp vẫn giữ parser mặc định cho tệp không hỗ trợ.

## Tài liệu và phụ thuộc

- `.agents/tasks/2026-10-25-rag15-llamaparse-parser`, `.agents/tasks/2026-10-25-upload-parser-selection`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai và test tự động đạt; self_review approved. Chưa kiểm tra thủ công với LlamaCloud thật.
- Blocker: không có.
- Bước tiếp theo: người dùng kiểm tra UI và merge nhánh `feat/llamaparse-tier-select` vào `dev`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-04T22:54:52+07:00 — claude-code: mã hóa tier trong tên parser (`llamaparse:<tier>`) thay vì thêm tham số mới, để dùng lại toàn bộ đường đi `parser_name` (API → job → pipeline → metadata → preview/rebuild/parse hàng loạt).

# Implementation: 2026-11-15-hide-chunk-placeholder-controls

## Tổng quan triển khai

Nhánh `feat/hide-chunk-placeholder-controls` (tách từ `dev` tại `a2891b2`). Triển khai theo đề xuất mặc định của Q-01 (gỡ khỏi giao diện) và Q-02 (gỡ nhãn "Văn bản"); người yêu cầu giao việc bằng lệnh "implement" cho task này.

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-11-15T21:10:44+07:00`.
- Trạng thái: `in_review`.
- Đã làm:
  - `frontend/src/DocumentView.jsx`: gỡ state `selectedChunkIds`, `enabledChunks` cùng comment đi kèm; gỡ handler `toggleSelectChunk`, `toggleSelectAllChunks`, `toggleEnableChunk`; gỡ "Chọn tất cả" khỏi thanh công cụ; gỡ ô chọn, nhãn "Văn bản" và công tắc `pill-switch` khỏi từng thẻ đoạn. Class thẻ chỉ còn `chunk-card-item` + `is-hovered-target`. Hover/click (`handleChunkHover`) giữ nguyên.
  - `frontend/src/styles/document.css`: gỡ khối "Chọn và bật/tắt từng đoạn" (`.chunk-select-all-label`, `.chunk-checkbox`, `.chunk-card-top-right`, `.chunk-type-tag`, bản thứ hai của `.chunk-card-item.selected`) và bản đầu của `.chunk-card-item.selected`. Gỡ rule `.chunk-card-top` cũ có `justify-content: space-between`: nếu giữ, khi không còn nhóm bên phải thì nhãn token sẽ bị đẩy sang mép phải. Rule `.chunk-card-top` còn lại xếp nhãn sát nhau bằng `gap`. Sửa comment khối nhãn cho đúng hiện trạng. File được ghi lại với LF (index đang LF; working tree trước đó là CRLF).
  - `pill-switch` trong `dataset.css` **giữ nguyên** vì `ConfigView.jsx` vẫn dùng (đã grep).
  - `frontend/src/DocumentView.pagination.test.jsx`: thêm test "renders chunk cards without placeholder select or enable controls". Test kiểm tra cột đoạn không có `role="switch"`, checkbox, chữ "Chọn tất cả" hay "Văn bản", và bấm thẻ vẫn gắn `is-hovered-target`. Đã xác nhận test này fail trên `DocumentView.jsx` cũ (tìm thấy nút switch) và pass trên bản mới.
- File thay đổi: 3 file trên; commit: xem `git log dev..feat/hide-chunk-placeholder-controls`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: không đổi API; không đổi `pill-switch` dùng chung.
- Kiểm tra đã chạy: `npm test` (35 file, 244 test pass), `npm run build` pass. Xem `verification.md`.
- Còn lại/blocker: kiểm tra trực quan trên trình duyệt chưa chạy (extension Chrome không kết nối được trong phiên này).

## Trao đổi giữa agents

Chưa có thông báo.

## Bàn giao

- `2026-11-15T21:10:44+07:00` — claude-code → người yêu cầu: S-01 đã xong trên nhánh `feat/hide-chunk-placeholder-controls` (commit `5d0ca5b`, `af03c09`). Việc cần làm tiếp: xem trực quan thẻ đoạn ở màn chi tiết tài liệu (sáng/tối).
- `2026-11-15T21:14:16+07:00` — claude-code: đã push nhánh và mở PR #68 (https://github.com/8thMay03/PTIT-Chatbot/pull/68) vào `dev` theo yêu cầu người yêu cầu.

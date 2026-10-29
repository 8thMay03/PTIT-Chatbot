# Task: Gộp Markdown thô và bản render thành một cột trong trình sửa Markdown

- ID: `2026-10-29-md-editor-toggle-view`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("trong trang sửa markdown, hãy gộp markdown thô và markdown bản render lại thành 1 màn
  thôi, có thể chuyển qua giữa 2 bản bằng 1 nút")
- Tạo lúc: `2026-10-29T22:10:00+07:00`
- Cập nhật lúc: `2026-10-29T22:20:59+07:00`

## Yêu cầu và kết quả mong muốn

Trình sửa Markdown (`MarkdownEditorView`) đang có ba cột: Bản gốc, Markdown thô, Bản render (kèm "Cuộn đồng bộ").
Cần gộp Markdown thô và Bản render thành một cột "Markdown"; một nút trên đầu cột chuyển qua lại giữa sửa thô và xem
bản render. Cột Bản gốc giữ nguyên để đối chiếu.

## Phạm vi

- Bao gồm: `frontend/src/components/MarkdownEditorView.jsx`, `MarkdownEditorView.test.jsx`,
  `frontend/src/styles/markdown-editor.css`.
- Ngoài phạm vi: API Markdown, luồng lưu/hoàn tác, cột Bản gốc, nơi gọi (`DocumentView`, `DatasetView`).
- Ràng buộc: không thêm thư viện; không mất lịch sử hoàn tác (Ctrl+Z) của ô sửa khi chuyển chế độ.

## Tiêu chí nghiệm thu

- [x] AC-01: Chỉ còn cột "Bản gốc" và cột "Markdown"; nút "Xem bản render"/"Sửa Markdown" chuyển giữa ô sửa thô và
  bản render; tiêu đề cột cho biết chế độ hiện tại; nội dung đang sửa (chưa lưu) hiện đúng trong bản render.
- [x] AC-02: Chuyển chế độ giữ vị trí cuộn tương đối; ô sửa không bị gỡ khi xem bản render.
- [x] AC-03: Lựa chọn cột kiểu cũ trong `localStorage` (`raw`/`rendered`) được đổi sang `markdown`, không làm mất
  cột.
- [x] AC-04: `npm test`, `npm run build`, `npm run check:bundle` đạt; 1280 sáng/tối và 390 px không cuộn ngang.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.

## Trạng thái hiện tại

- Tóm tắt: `done` — S-01 xong, V-01 … V-04 `passed`, review `self_review` `approved`.
- Blocker: không.
- Bước tiếp theo: người dùng xem thử; merge `feat/md-editor-toggle-view` vào `dev` khi đồng ý.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-29T22:10:00+07:00` — `claude-agent`: tạo task, chuyển thẳng `in_progress` theo yêu cầu trực tiếp.
- `2026-10-29T22:20:59+07:00` — `claude-agent`: hoàn tất, chuyển `done`.

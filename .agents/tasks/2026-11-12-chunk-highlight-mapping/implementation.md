# Implementation: 2026-11-12-chunk-highlight-mapping

## Tổng quan triển khai

Nhánh `feat/chunk-highlight-mapping` (tách từ `dev` tại `20e1b92`).

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-11-12T23:58:00+07:00`.
- Đã làm:
  - `chunkLocator.js`: tài liệu và đoạn cùng đi qua `renderMarkdownHtml`; chữ của mỗi text node gán cho khối gần nhất (`p`, `h1-6`, `li`, `tr`, `blockquote`, `pre`) nên khối lồng nhau không bị đếm hai lần; chuẩn hóa NFC + chữ thường + chỉ giữ chữ/số.
  - Đoạn được cắt thành mảnh ~48 ký tự; tìm mọi vị trí của từng mảnh trên chuỗi tài liệu rồi quy hoạch động chọn chuỗi mảnh đúng thứ tự, khoảng hở ≤ 250 ký tự, trừ 0.5 điểm mỗi ký tự hở (vùng liền mạch thắng vùng ghép từ hai chỗ na ná nhau).
  - Dòng heading chép vào đầu mỗi đoạn con được tách khỏi chuỗi mảnh; chỉ dùng để cộng điểm khi heading đó là duy nhất trong tài liệu, và được đánh dấu khi đứng ngay trước phần thân.
  - Khi còn nhiều vùng gần ngang điểm (≥ 90%), định vị đoạn đứng trước trong danh sách đang hiển thị rồi chọn vùng đầu tiên nằm sau nó (đệ quy, chỉ khi mơ hồ); kết quả nhớ theo danh sách nên không phụ thuộc thứ tự trỏ chuột.
  - Không đủ căn cứ thì không đánh dấu (bỏ đoán theo tỷ lệ).
  - `DocumentView.jsx`: bỏ `cleanMarkdown`/`extractChunkSnippets`/`findMatchingElements`; giữ bộ định vị trong ref theo nội dung tài liệu; `visibleChunks` dùng `useMemo`; tỷ lệ ước lượng dùng tổng số đoạn của tài liệu cả khi tìm kiếm.
- File thay đổi: `frontend/src/lib/chunkLocator.js`, `frontend/src/lib/chunkLocator.test.js`, `frontend/src/DocumentView.jsx`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: không có.
- Kiểm tra đã chạy: `verification.md` V-01…V-03.
- Còn lại/blocker: chưa kiểm tra thủ công trên trình duyệt.

## Trao đổi giữa agents

- Không có.

## Bàn giao

### HANDOFF-claude-code-001 — S-01

- Từ / đến: `claude-code` / người dùng.
- Đã hoàn tất: S-01.
- File/branch/commit/patch: nhánh `feat/chunk-highlight-mapping`; commit xem `git log`. Thay đổi file PDF trong `data/` (xóa ở `data/`, thêm ở `data/raw/`) là của người dùng, không nằm trong commit.
- Kiểm chứng: V-01…V-03 `passed`.
- Review: `self_review` `approved`.
- Hạn chế / còn lại: chưa kiểm tra trên trình duyệt; giới hạn đã biết ghi trong `review.md`.
- Bước tiếp theo: người dùng kiểm tra trên trình duyệt (container frontend chạy Vite dev theo nhánh đang checkout) rồi tạo PR vào `dev`.
- Phản hồi nhận bàn giao: chờ người dùng.

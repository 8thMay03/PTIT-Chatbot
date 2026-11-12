# Task: Giữ mục lục tài liệu trong index (chunk mục lục riêng)

- ID: `2026-11-12-keep-toc-chunks`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: người dùng (8thMay03)
- Tạo lúc: `2026-11-12T23:07:59+07:00`
- Cập nhật lúc: `2026-11-12T23:20:00+07:00`

## Yêu cầu và kết quả mong muốn

Người dùng phát hiện bảng mục lục đầu "Sổ tay sinh viên D26 _1_.pdf" (dataset `default`) mất hoàn toàn sau khi chunk. Nguyên nhân: `cleaner._drop_noise_lines` bỏ cả section "MỤC LỤC" (quyết định RAG-06 AC-03, giữ lại ở table-chunking-coverage AC-06). `parsed_text` vẫn còn mục lục; chỉ index mất.

Người dùng quyết định giữ mục lục để trả lời được câu hỏi về cấu trúc tài liệu ("Sổ tay gồm những phần nào?", "Khóa 2026 có những chương trình nào?", "… ở trang mấy?").

## Phạm vi

- Bao gồm: `backend/app/ingestion/cleaner.py` (giữ section mục lục, chuẩn hóa entry, header bảng mục lục), cờ `is_toc` trong metadata chunk (`pipeline.py`), cập nhật test/docstring liên quan, chunk lại index local và đo retrieval.
- Ngoài phạm vi: hạ trọng số chunk mục lục khi xếp hạng (chỉ làm nếu eval cho thấy cần); entry mục lục lạc ngoài section "MỤC LỤC" vẫn bị lọc như cũ.
- Ràng buộc: thay thế AC-03 (phần "chunk mục lục") của RAG-06 và vế "bảng mục lục thật trong D26 vẫn bị lọc" của AC-06 table-chunking-coverage — theo quyết định của người dùng.

## Tiêu chí nghiệm thu

- [x] AC-01: Sau cleaner, section "MỤC LỤC" được giữ: bảng mục lục giữ mọi hàng, bảng 2 cột có hàng đầu là entry được thêm header `|Mục|Trang|`; entry dạng chấm dẫn/số trang đậm được viết lại thành `… (trang N)`; entry mục lục lạc ngoài section vẫn bị lọc; cleaner idempotent. — đạt (V-01)
- [x] AC-02: Chunk thuộc section "MỤC LỤC" có `metadata.is_toc = true`, chunk khác `false`; mỗi chunk mục lục mang header bảng, không vi phạm bất biến bảng. — đạt (V-02)
- [x] AC-03: Index local D26 được chunk lại, có chunk mục lục chứa đủ entry từ "Lời nói đầu|3" đến "Vui chơi, giải trí|268", embed đủ. — đạt (V-03)
- [x] AC-04: hit@4/hit@10 bm25 và hybrid trên `ptit_ragas_100.json` không thấp hơn baseline cùng ngày trước khi sửa; không có câu nào được tính "trúng" chỉ nhờ chunk mục lục. — đạt (V-04)
- [x] AC-05: Toàn bộ test backend xanh. — đạt (V-05)

## Tài liệu và phụ thuộc

- `.agents/tasks/2026-10-25-rag06-article-clause-chunking/` (AC-03 gốc), `.agents/tasks/2026-11-05-table-chunking-coverage/` (AC-06).
- Báo cáo eval: `documents/rag-eval/keep-toc/README.md`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai, test xanh, index local đã chunk lại, eval không thụt lùi. Mới có self-review.
- Blocker: không có.
- Bước tiếp theo: người dùng xem PR/diff; reviewer độc lập (nếu có) review trước khi merge vào `dev`.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-11-12T23:07:59+07:00` — `claude-code`: tạo task theo yêu cầu người dùng "giữ lại mục lục"; chọn giữ section mục lục thành chunk riêng có cờ `is_toc`, chưa hạ trọng số khi xếp hạng, quyết định theo kết quả eval.
- `2026-11-12T23:20:00+07:00` — `claude-code`: eval không thụt lùi ở hit@4/hit@10 → không thêm hạ trọng số; chuyển `in_review`.

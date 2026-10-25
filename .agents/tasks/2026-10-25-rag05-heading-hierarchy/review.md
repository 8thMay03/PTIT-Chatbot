# Review: 2026-10-25-rag05-heading-hierarchy

- Reviewer: `claude-code-agent`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `feat/rag05-heading-hierarchy` (tách từ `dev`) (nền `9d67b581ee6d`, chưa commit). Diff gồm `backend/app/parsers/{normalize.py,__init__.py,docling.py}`, `backend/scripts/{check_structure.py,eval_retrieval.py}`, `backend/tests/{test_markdown_normalizer.py,test_check_structure.py,test_eval_retrieval.py,test_document_converters.py}`, fixture `heading-normalization/`, `documents/rag-eval/{README.md,rag-05/}`.
- Cập nhật lúc: `2026-10-25T09:04:25+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-07; S-01…S-04.
- Bằng chứng kiểm chứng: `verification.md` V-01…V-08 (tất cả `passed`).
- Điểm đã đánh giá:
  - tính đúng của luật gán cấp trên toàn bộ D26 (đọc cây heading của cả hai bản);
  - idempotent;
  - không đổi văn bản thường;
  - tương thích các test cũ;
  - phạm vi file (sửa `eval_retrieval.py` của RAG-01 chỉ bằng phần bổ sung);
  - không ghi secret, không sửa `data/`.

## Nhận xét

### R-01 — section_dominance đúng biên ngưỡng

- Vị trí: `documents/rag-eval/rag-05/processed_hybrid.json` (`max_share` 0.150).
- Liên quan: AC-05.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: AC đạt (không vượt 15%) nhưng không còn dư địa. "Điều 25. Thang điểm đánh giá" (4.486 ký tự) xuất hiện trong top-4 của 15 câu, và dao động của chỉ mục vector sau ingest có thể đẩy chỉ số lên 0.16.
- Đề nghị xử lý: RAG-06 (chunking theo Khoản, header ngữ cảnh) sẽ chia nhỏ các Điều dài. Đo lại `section_dominance` sau RAG-06.
- Người xử lý: RAG-06.
- Nếu deferred: AC hiện đạt; theo dõi bằng `--compare` ở RAG-06.

### R-02 — Heuristic vị trí heading "other"

- Vị trí: `backend/app/parsers/normalize.py` (`_render`, `_is_block_caption`, `introduces`).
- Liên quan: AC-02 (gián tiếp).
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động:
  - Dòng in đậm không có cấp gốc được đoán là anh em, hoặc là con nếu kết thúc bằng ":". Caption viết hoa sau Chương/Điều được coi là khối mới.
  - Còn ca lệch: "MỘT SỐ ỨNG DỤNG CHUYỂN ĐỔI SỐ CHO SINH VIÊN" nằm dưới "HƯỚNG DẪN THỦ TỤC HÀNH CHÍNH…" (cấp 3) thay vì ngang hàng.
  - Không ảnh hưởng Điều hay CTĐT; chỉ ảnh hưởng path của vài section phụ.
- Đề nghị xử lý: soát lại khi thêm tài liệu mới bằng `check_structure --tree`.
- Người xử lý: `claude-code-agent` / task sau.

### R-03 — PHỤ LỤC cấp 2 không mang tên quy định cha

- Vị trí: `normalize.py` (`_TITLE`).
- Liên quan: spec RAG-05, RAG-12.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: theo spec, PHỤ LỤC ngang hàng tiêu đề văn bản, nên `PHỤ LỤC 1` của quy định tiếng Anh và của quy định CTSV chỉ phân biệt nhau bằng tên phụ lục. Tên phụ lục trong D26 đều tự mô tả.
- Đề nghị xử lý: xem lại trong RAG-12 (citation phân biệt quy định trùng số).
- Người xử lý: RAG-12.

### R-04 — Dòng thường bắt đầu bằng "Điều N." luôn được nâng thành heading

- Vị trí: `normalize.py` (`_promotes_plain`).
- Liên quan: AC-01.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: cần thiết để đạt AC-01 (D26 có 4 dòng Điều không định dạng). Với tài liệu mới, một dòng ≤ 200 ký tự nằm giữa đoạn văn mà bắt đầu bằng "Điều 5. …" sẽ thành heading giả.
- Đề nghị xử lý: không đổi lúc này. `check_structure` (cây và `article_numbering`) giúp phát hiện.
- Người xử lý: theo dõi khi ingest tài liệu mới.

### R-05 — Thay đổi hành vi với Markdown người dùng tải lên

- Vị trí: `backend/app/parsers/__init__.py`.
- Liên quan: S-01.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `resolved` (chủ đích, đã ghi lại).
- Vấn đề và tác động: mọi `.md`/`.txt` qua `read_document_text` (ingest, preview) giờ có cấp heading và escape đã chuẩn hóa. Đây chính là yêu cầu "chạy sau mọi parser". Văn bản không có cấu trúc giữ nguyên (`test_plain_text_without_structure_is_unchanged`, `test_text_files_are_read_directly`).
- Xác nhận của reviewer: đã ghi trong `implementation.md` S-01.

## Lịch sử các vòng review

- `2026-10-25T09:04:25+07:00` — `claude-code-agent` — working tree như trên — `approved`. R-01…R-04 `low` deferred có hướng theo dõi; R-05 resolved.

## Kết luận

- Kết luận: `approved` (self_review).
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01 (RAG-06), R-02, R-03 (RAG-12), R-04.
- Phần chưa review / giới hạn: không có review độc lập. Các script tạm (ingest một tài liệu, kiểm tra DB) nằm ở scratchpad, không thuộc diff.
- Bước tiếp theo: người dùng xem diff và quyết định commit.

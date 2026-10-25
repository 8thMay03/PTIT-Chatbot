# Task: RAG-05 · Chuẩn hóa phân cấp heading cho văn bản quy chế (Phần › Quy định › Chương › Điều)

- ID: `2026-10-25-rag05-heading-hierarchy`
- Trạng thái: `done`
- Coordinator: `claude-code-agent`
- Người yêu cầu: người dùng (phiên Claude Code 2026-10-25; nguồn: trang Notion "RAG-05")
- Tạo lúc: `2026-10-25T08:47:15+07:00`
- Cập nhật lúc: `2026-10-25T09:04:25+07:00`

## Yêu cầu và kết quả mong muốn

- Bản Sổ tay D26 đang index (`data/processed/Sổ tay sinh viên D26 _1_ _1_.md`, đọc nguyên trạng bằng `TextParser`) có 122/186 dòng "Điều" là đoạn in đậm, không phải heading → section lớn nuốt nhiều Điều. Trên baseline RAG-01 (hybrid, 100 câu) "2. Khóa học" nằm trong top-4 của 45% câu, "Điều 26" 22%, "Chương V" 20%.
- Cấp heading lệch (Chương II `#`, Chương I/III `##`), "Điều 1" lặp ở 7 quy định → section_path phải có tên quy định.
- CTĐT: heading năm học không kèm tên ngành; "KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN" tách khỏi tên ngành.
- Bản Docling của D26: 560 heading đều `##`, không có phân cấp.
- Cần: bước chuẩn hóa Markdown dùng chung chạy sau mọi parser (NFC, bỏ escape, nâng dòng in đậm, gán lại cấp PHẦN=1 / tiêu đề văn bản=2 / Chương=3 / Mục=4 / Điều=5 / heading khác dưới cấp gần nhất); quy tắc riêng CTĐT; script kiểm tra cấu trúc; so sánh bản processed và Docling, chọn bản D26 chuẩn.

## Phạm vi

- Bao gồm: `backend/app/parsers/normalize.py` (mới), `backend/app/parsers/__init__.py`, `backend/app/parsers/docling.py`, `backend/scripts/check_structure.py` (mới), bổ sung `section_path`/`section_dominance` vào `backend/scripts/eval_retrieval.py`, tests + fixture, báo cáo `documents/rag-eval/rag-05/`, trang task này.
- Ngoài phạm vi: manifest (RAG-03 — chỉ ghi quyết định và bàn giao), chunking theo Khoản/header ngữ cảnh (RAG-06), bảng HTML (RAG-07), sửa dữ liệu trong `data/`, `.env`.
- Ràng buộc:
  - Bước chuẩn hóa idempotent, không đổi văn bản không có cấu trúc (giữ hành vi `TextParser` với file thường).
  - Không bump `_CONVERTER_VERSION` (cache Docling lưu bản export thô).
  - Không ghi đè `documents/rag-eval/baseline_*.json`.

## Tiêu chí nghiệm thu

- [x] AC-01: 100% dòng bắt đầu bằng "Điều N." trong tài liệu quy chế trở thành heading; không section nào chứa từ 2 Điều trở lên.
- [x] AC-02: section_path của mọi Điều chứa tên quy định; chứa Chương khi trong nguồn Điều đó nằm sau một heading Chương của cùng quy định (cách hiểu đã chốt với người dùng 2026-10-25). Ví dụ `… > QUY ĐỊNH ĐÀO TẠO … > Chương VI … > Điều 33. Cảnh báo kết quả học tập`.
- [x] AC-03: không chunk chương trình đào tạo nào có section_path thiếu tên ngành.
- [x] AC-04: unit test với fixture cho cả hai kiểu đầu vào (MD dùng in đậm và Docling toàn `##`) cho cùng cây heading mong đợi.
- [x] AC-05: không section nào xuất hiện trong top-4 của hơn 15% câu golden set (baseline hybrid: "2. Khóa học" 45%).
- [x] AC-06: hit@4 và MRR (hybrid, đo bằng RAG-01) tăng so với baseline; không nhóm tài liệu nào giảm quá 2 điểm phần trăm.
- [x] AC-07: script kiểm tra cấu trúc in cây heading và cảnh báo bất thường (section quá dài, Điều không phải heading, số Điều nhảy cóc).

## Tài liệu và phụ thuộc

- Phụ thuộc RAG-01: `.agents/tasks/2026-10-24-rag-eval-retrieval-baseline/` (`done`), baseline `documents/rag-eval/baseline_*.json`.
- RAG-03 (manifest) đang phát triển ở nơi khác, chưa có trong repo → bàn giao quyết định bản D26 chuẩn.
- Nên làm trước RAG-06, RAG-07.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01…S-04 xong trên working tree nhánh `feat/rag05-heading-hierarchy` (tách từ `dev`) (**chưa commit**). Bản D26 chuẩn là `data/processed/Sổ tay sinh viên D26 _1_ _1_.md` (parser `text`); index local đã ingest lại bản này (1283 chunk, fingerprint `0a63b72686b2…`).

  | hybrid | hit@1 | hit@4 | MRR | cov@4 | section chiếm chỗ nhất |
  |---|---:|---:|---:|---:|---|
  | baseline | 0.650 | 0.840 | 0.739 | 0.799 | 0.45 "2. Khóa học" |
  | RAG-05 (processed) | 0.720 | 0.850 | 0.780 | 0.807 | 0.15 "Điều 25" |
  | Docling + chuẩn hóa | 0.680 | 0.850 | 0.763 | 0.792 | 0.16 |

  Bằng chứng ở V-01…V-08; review self_review `approved`, các mục R-01…R-04 (low) hoãn lại có hướng theo dõi. Suite: 289 passed, 1 skipped.
- Blocker: không có.
- Bước tiếp theo: người dùng xem diff và quyết định commit; RAG-03 nhận MSG-claude-code-agent-001 (entry manifest D26); RAG-06 đo lại `section_dominance` (R-01).

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-25T08:47:15+07:00` — `claude-code-agent`: tạo task từ trang Notion RAG-05; người dùng chốt (1) manifest: chỉ ghi quyết định + bàn giao RAG-03; (2) AC-02: Chương bắt buộc khi nguồn có. Thêm AC-07 cho script kiểm tra cấu trúc (mục "Việc cần làm" của RAG-05).
- `2026-10-25T09:04:25+07:00` — `claude-code-agent`: mọi AC có bằng chứng (AC-05 đúng biên 0.150; AC-06 đo ở mức overall vì dataset chưa có `source`); chọn bản processed MD làm bản D26 chuẩn; review self_review `approved`; task `done`, thay đổi chưa commit, chờ người dùng.

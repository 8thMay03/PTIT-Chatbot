# Implementation: 2026-10-25-rag05-heading-hierarchy

## Tổng quan triển khai

S-01…S-04 đã tích hợp trên working tree nhánh `feat/rag05-heading-hierarchy` (tách từ `dev`) (nền `9d67b581ee6d`, **chưa commit**). Index local đã được ingest lại bằng bản processed MD sau chuẩn hóa (1 tài liệu, 1283 chunk, fingerprint `0a63b72686b2…`).

## Nhật ký theo nhiệm vụ

### S-01 — claude-code-agent

- Cập nhật lúc: `2026-10-25T09:04:25+07:00`.
- Đã làm: thêm `normalize_markdown()` tại `backend/app/parsers/normalize.py`. Các bước:
  - NFC, `&amp;`→`&`, `\_`→`_`, CRLF→LF.
  - Nhận diện heading ATX, dòng in đậm trọn dòng và dòng thường mang mẫu cấu trúc (≤ 200 ký tự). Bỏ qua code fence, bảng HTML và bảng Markdown.
  - Ghép nhãn trần `PHẦN IV`/`Chương VII` với tiêu đề dòng sau. Nếu phần đã ghép kết thúc bằng dấu phẩy thì ghép tiếp, ví dụ `PHẦN IV` + `MỘT SỐ QUY CHẾ,` + `QUY ĐỊNH VỀ QUẢN LÝ ĐÀO TẠO`.
  - Tách heading dính `Chương V : … Điều 23. …` (lỗi của Docling).
  - Ghép heading trần `KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN` với tên ngành ở dòng sau.
  - Hạ các mục trong MỤC LỤC (kết thúc bằng số trang) về dòng thường.
  - Gán cấp: PHẦN=1; tiêu đề văn bản/PHỤ LỤC/`II/ Quyết định số…` và heading CTĐT=2; Chương và CHUYÊN NGÀNH=3; Mục và NĂM HỌC/HỌC KỲ=4; Điều=5. CHUYÊN NGÀNH và NĂM HỌC/HỌC KỲ chỉ được nhận trong ngữ cảnh CTĐT.
  - Heading khác nằm dưới cấp cấu trúc gần nhất và giữ quan hệ lồng nhau tương đối, tối đa cấp 6. Dòng in đậm kết thúc bằng ":" là con của heading trước, dòng in đậm khác là anh em.
  - Caption viết hoa (không đánh số, ≥ 3 từ) nằm sau Chương/Điều và ngoài CTĐT được nâng lên cấp 2, để "LỊCH TIẾP SINH VIÊN…" hay "MỘT SỐ CHÍNH SÁCH CỦA NHÀ NƯỚC…" không bị gắn làm con của Điều cuối cùng.
  - Nhãn được chuẩn về một dạng `Chương V: …`.
- Nối vào `read_document_text` (`backend/app/parsers/__init__.py`), nên mọi parser đều đi qua bước này. `docling.py` chỉ giữ phần riêng của Docling (bỏ `<!-- image -->`, nén padding bảng); NFC, `&amp;` và nâng dòng in đậm đã chuyển sang module chung. Không bump `_CONVERTER_VERSION` vì cache lưu bản export thô.
- File thay đổi: `backend/app/parsers/normalize.py` (mới), `backend/app/parsers/__init__.py`, `backend/app/parsers/docling.py`, `backend/tests/test_markdown_normalizer.py` (mới), `backend/tests/fixtures/corpus/heading-normalization/{bold-md,docling-flat}.md` (mới), `backend/tests/test_document_converters.py` (kỳ vọng mới: `HƯỚNG DẪN…` cấp 2, `1. Khai báo…` cấp 3).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: mọi văn bản qua `read_document_text`, kể cả preview upload và file `.md` người dùng tải lên, giờ có cấp heading đã chuẩn hóa. Văn bản không có cấu trúc giữ nguyên (có test).
- Kiểm tra đã chạy: xem V-01…V-04, V-08.
- Còn lại/blocker: không có.

### S-02 — claude-code-agent

- Cập nhật lúc: `2026-10-25T09:04:25+07:00`.
- Đã làm: `backend/scripts/check_structure.py` đọc tài liệu qua `read_document_text(convert=False)`. Script in cây heading (`--tree`: dòng, cấp, loại, số ký tự) và gom cảnh báo theo mã:
  - lỗi cứng: `article_not_heading`, `multiple_articles`, `article_without_title`, `article_without_chapter`, `program_without_name`, `plan_outside_program`;
  - cảnh báo: `long_section`, `article_numbering`.
  - `--strict` trả exit code 1 khi có lỗi cứng. Tóm tắt liệt kê số Điều không có Chương (hợp lệ theo cách hiểu AC-02).
- File thay đổi: `backend/scripts/check_structure.py`, `backend/tests/test_check_structure.py` (mới, 8 test).
- Kiểm tra đã chạy: V-07.

### S-03 — claude-code-agent

- Cập nhật lúc: `2026-10-25T09:04:25+07:00`.
- Đã làm: `eval_retrieval.py` lên schema v3, gồm:
  - `retrieved[].section_path`;
  - `metrics.section_dominance` (`k`, `max_share`, `top[]`) qua hàm thuần `section_dominance()`/`section_key()`;
  - `report_dominance()` tự tính lại từ `heading` cho báo cáo cũ;
  - `print_summary` và `--compare` in phần dominance.
  - Ngoài ra, `main()` gọi `sys.stdout.reconfigure(encoding="utf-8")`, vì `--compare` bị lỗi `UnicodeEncodeError` (cp1252) khi stdout được chuyển hướng ra file.
- File thay đổi: `backend/scripts/eval_retrieval.py`, `backend/tests/test_eval_retrieval.py` (+2 test). Các khóa và chỉ số cũ giữ nguyên (`--compare` với `baseline_*.json` v2 vẫn chạy).
- Kiểm tra đã chạy: V-05, V-08.

### S-04 — claude-code-agent

- Cập nhật lúc: `2026-10-25T09:04:25+07:00`.
- Đã làm:
  - Chạy `check_structure` trên cả hai bản D26: processed 0 lỗi / 12 cảnh báo, Docling 0 lỗi / 15 cảnh báo.
  - Ingest từng bản bằng script tạm ở scratchpad (không commit). Script thay `pipeline.load_documents` bằng danh sách đúng một tài liệu rồi gọi `ingest_documents()`, nên chỉ thay index local; không dùng `delete_ingested_document` vì hàm này xóa luôn file nguồn.
  - Chạy eval hybrid + bm25, lưu `documents/rag-eval/rag-05/{processed,docling}_{hybrid,bm25}.json`.
  - Chọn bản processed và ingest lại để index local ở trạng thái cuối. Thêm mục RAG-05 vào `documents/rag-eval/README.md`.
- Quyết định: **bản chuẩn D26 = `data/processed/Sổ tay sinh viên D26 _1_ _1_.md`, parser `text`**. Ở hybrid, bản này hơn Docling trên mọi chỉ số (hit@1 0.720 so với 0.680, MRR 0.780 so với 0.763, cov@4 0.807 so với 0.792) và đạt dominance ≤ 15% (0.15 so với 0.16). Văn bản Docling còn lỗi thứ tự đọc: tiêu đề Nghị định 238 dính đoạn "Lắng nghe giảng viên…", Điều 16 đứng trước Điều 12.
- Kiểm tra đã chạy: V-05, V-06.

## Trao đổi giữa agents

### MSG-claude-code-agent-001

- Lúc: `2026-10-25T09:04:25+07:00`.
- Từ: `claude-code-agent`; đến: người phụ trách RAG-03 (manifest).
- Nhiệm vụ: `S-04`.
- Loại: `handoff`.
- Tham chiếu: không có.
- Nội dung:
  - RAG-05 đã so sánh hai bản Sổ tay D26 sau bước chuẩn hóa chung và chọn **`data/processed/Sổ tay sinh viên D26 _1_ _1_.md`** (parser `text`, `doc_type` sổ tay, khóa 2026) làm bản `active`.
  - `data/raw/Sổ tay sinh viên D26.pdf` nên ở trạng thái không index (cùng nội dung, chất lượng văn bản Docling kém hơn). Có thể giữ lại làm nguồn gốc.
  - Số liệu: `documents/rag-eval/README.md` mục "RAG-05".
  - Trong repo chưa có manifest nên RAG-05 không tạo entry.
- Hành động mong muốn: khi tạo `data/manifest.*`, thêm entry D26 theo quyết định trên. Nếu đổi bản chuẩn, chạy lại `python -m scripts.check_structure <file> --strict` và eval hybrid.

## Bàn giao

### HANDOFF-claude-code-agent-001 — S-01…S-04

- Từ / đến: `claude-code-agent` / người dùng (coordinator phê duyệt commit).
- Đã hoàn tất: module chuẩn hóa, script kiểm tra cấu trúc, section_dominance trong eval, so sánh và chốt bản D26, báo cáo + README.
- File/branch/commit/patch: working tree nhánh `feat/rag05-heading-hierarchy` (tách từ `dev`), chưa commit.
- Kiểm chứng: `verification.md` V-01…V-08.
- Review: `review.md` (self_review).
- Hạn chế / còn lại:
  - dominance 0.150 nằm đúng ngưỡng 15%;
  - 2 câu mất hit@4 (chi tiết trong README);
  - dataset chưa có `source` nên chưa đo được theo nhóm tài liệu;
  - manifest chờ RAG-03.
- Bước tiếp theo: người dùng xem diff và quyết định commit; RAG-03 nhận MSG-claude-code-agent-001; RAG-06/07 có thể dựa vào section_path mới.

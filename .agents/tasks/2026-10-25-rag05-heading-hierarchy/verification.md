# Verification: 2026-10-25-rag05-heading-hierarchy

- Verifier: `claude-code-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `feat/rag05-heading-hierarchy` (tách từ `dev`) (nền `9d67b581ee6d`, chưa commit), gồm các file trong `implementation.md`.
- Môi trường: Windows 11, `backend/.venv` (Python 3.11), PostgreSQL pgvector local, embedding OpenAI `text-embedding-3-small` (câu hỏi lấy từ cache, 0 miss), dataset `backend/tests/fixtures/ptit_ragas_100.json` (100 câu).

## Kiểm chứng tiêu chí

### V-01 — AC-01 (Điều thành heading; không section nào có ≥ 2 Điều)

- Người thực hiện / thời gian: `claude-code-agent` / `2026-10-25T09:00+07:00`.
- Loại: script kiểm tra cấu trúc + truy vấn chunk trong DB + unit test.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `.venv\Scripts\python -m scripts.check_structure "..\data\processed\Sổ tay sinh viên D26 _1_ _1_.md"`; script tạm đếm `parent_text` chứa > 1 heading `Điều N`; `pytest tests/test_markdown_normalizer.py -k "no_chunk_spans_two_articles"`.
- Kỳ vọng: 0 `article_not_heading`, 0 `multiple_articles`; 0 parent chunk chứa 2 Điều.
- Kết quả thực tế: check_structure báo 0 lỗi cứng, 189 heading Điều (trước chuẩn hóa: 122 Điều chỉ là đoạn in đậm, cộng 4 dòng Điều là văn bản thường). DB có 1283 chunk, `parents_with_2+_articles=0`. Test đạt cho cả hai fixture. Bản Docling cũng 0 lỗi, 189 Điều.
- Trạng thái: `passed`.
- Bằng chứng: output lệnh trong phiên; tóm tắt `570 heading (article=189, chapter=35, …); 0 lỗi, 12 cảnh báo`.

### V-02 — AC-02 (section_path của Điều có tên quy định và Chương)

- Người thực hiện / thời gian: `claude-code-agent` / `2026-10-25T09:00+07:00`.
- Loại: script kiểm tra cấu trúc + truy vấn DB + unit test.
- Lệnh / thao tác: check_structure (`article_without_title`, `article_without_chapter`); script tạm duyệt 506 chunk có `Điều N.` trong section_path, kiểm tra path có tiêu đề văn bản; `pytest -k article_section_path`.
- Kỳ vọng: 0 Điều thiếu tiêu đề; 0 Điều thiếu Chương khi quy định đã có Chương phía trên (cách hiểu chốt 2026-10-25).
- Kết quả thực tế: 0 lỗi `article_without_title` và `article_without_chapter`. DB: 506 chunk của Điều, `missing_title=0`. Có 45 Điều không có Chương; đây là các quy định "lược trích" không có Chương phía trên (QUY ĐỊNH ĐÀO TẠO SINH VIÊN TÀI NĂNG, phần đầu quy định thi, thực tập, tiếng Anh, Quyết định 05/2022…). Ví dụ path thực tế: `PHẦN IV: MỘT SỐ QUY CHẾ, QUY ĐỊNH VỀ QUẢN LÝ ĐÀO TẠO > QUY ĐỊNH ĐÀO TẠO ĐẠI HỌC THEO TÍN CHỈ CỦA HỌC VIỆN > Chương VI: XỬ LÝ HỌC TẬP > Điều 33. Cảnh báo kết quả học tập`.
- Trạng thái: `passed`.
- Bằng chứng: output trong phiên; test fixture.

### V-03 — AC-03 (chunk CTĐT có tên ngành)

- Người thực hiện / thời gian: `claude-code-agent` / `2026-10-25T09:00+07:00`.
- Loại: script kiểm tra cấu trúc + truy vấn DB + unit test.
- Lệnh / thao tác: check_structure (`program_without_name`, `plan_outside_program`); script tạm duyệt chunk có heading "KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN" hoặc heading năm học/chuyên ngành trong section_path; `pytest -k study_plan_chunks`.
- Kỳ vọng: mọi chunk CTĐT có heading ngành (kèm tên) trong path.
- Kết quả thực tế: check_structure báo 0 lỗi; có 36 heading program, đều kèm tên ngành sau khi ghép. Script tạm ban đầu cho 15 cảnh báo, nhưng đều là dương tính giả của chính script: section "Học kỳ ……Năm học……" thuộc PHỤ LỤC 2 (phiếu đánh giá rèn luyện, ngoài CTĐT) bị khớp do script cho rằng mọi path đều ở ngữ cảnh CTĐT. Normalizer xếp heading này là `other` (đúng). Loại các mục đó ra, 455 chunk CTĐT đều có tên ngành.
- Trạng thái: `passed`.
- Bằng chứng: output trong phiên.

### V-04 — AC-04 (fixture hai kiểu đầu vào cho cùng cây heading)

- Người thực hiện / thời gian: `claude-code-agent` / `2026-10-25T08:58+07:00`.
- Loại: test tự động.
- Lệnh / thao tác: `.venv\Scripts\python -m pytest tests/test_markdown_normalizer.py -q`.
- Kỳ vọng: `bold-md.md` và `docling-flat.md` đều ra đúng `EXPECTED_TREE` (36 heading); idempotent.
- Kết quả thực tế: 29 test của file đạt (gồm tham số hóa cho cả hai fixture).
- Trạng thái: `passed`.

### V-05 — AC-05 (không section nào > 15% câu trong top-4)

- Người thực hiện / thời gian: `claude-code-agent` / `2026-10-25T09:02+07:00`.
- Loại: eval retrieval.
- Lệnh / thao tác: `python -m scripts.eval_retrieval --mode hybrid --output documents/rag-eval/rag-05/processed_hybrid.json`; `--compare ..\documents\rag-eval\baseline_hybrid.json ..\documents\rag-eval\rag-05\processed_hybrid.json`.
- Kỳ vọng: `section_dominance.max_share` ≤ 0.15.
- Kết quả thực tế: baseline 0.450 ("2. Khóa học") → **0.150** ("Điều 25. Thang điểm đánh giá", 15/100 câu). BM25: 0.42 → 0.15. Docling hybrid: 0.16, không đạt.
- Trạng thái: `passed`, nhưng nằm đúng biên ngưỡng (xem R-01).
- Bằng chứng: `documents/rag-eval/rag-05/processed_hybrid.json`.

### V-06 — AC-06 (hit@4, MRR hybrid tăng; không nhóm nào giảm > 2 điểm)

- Người thực hiện / thời gian: `claude-code-agent` / `2026-10-25T09:02+07:00`.
- Loại: eval retrieval.
- Lệnh / thao tác: như V-05, cộng script tạm liệt kê các câu đổi trạng thái hit@4.
- Kỳ vọng: hit@4 và MRR > baseline (0.840 / 0.739); không nhóm nào giảm > 0.02.
- Kết quả thực tế:
  - hit@4 0.840 → **0.850**, MRR 0.739 → **0.780**, hit@1 0.650 → 0.720, cov@4 0.799 → 0.807.
  - Các nhóm hiện có (`by_diacritics.co_dau`, `by_question_type.unknown`, `by_source.unknown`) đều bằng overall nên không giảm.
  - Theo từng câu: 3 câu có thêm hit@4, 2 câu mất (`student_card_initial_deadline` rank 1→7, `exam_review_form_destination` 3→ngoài top-10).
  - Ngoài AC: hit@10 giữ 0.900; cov@10 0.858 → 0.853.
- Trạng thái: `passed`, có giới hạn: dataset chưa có trường `source` nên chưa đo được "nhóm tài liệu" thật sự (chờ RAG-02).
- Bằng chứng: `documents/rag-eval/rag-05/processed_hybrid.json`, README mục RAG-05.

### V-07 — AC-07 (script kiểm tra cấu trúc)

- Người thực hiện / thời gian: `claude-code-agent` / `2026-10-25T08:59+07:00`.
- Loại: test tự động + chạy thực tế.
- Lệnh / thao tác: `pytest tests/test_check_structure.py -q`; `python -m scripts.check_structure <processed.md> --tree`; `… "..\data\raw\Sổ tay sinh viên D26.pdf" --parser docling`.
- Kỳ vọng: in cây heading; cảnh báo section dài, Điều không phải heading, số Điều nhảy cóc; `--strict` trả 1 khi có lỗi.
- Kết quả thực tế: 8 test đạt. Trên D26 thật, script phát hiện 11 (processed) và 13 (Docling) chỗ số Điều nhảy cóc do "lược trích", 1–2 section dài (bảng phiếu rèn luyện 12.838 ký tự; Docling: MỤC LỤC, "Điều 10. Tổ chức thực hiện" 10.788 ký tự). Trên MD thô chưa chuẩn hóa (fixture), script báo `article_not_heading` và `multiple_articles` (có test).
- Trạng thái: `passed`.

### V-08 — Hồi quy toàn bộ suite và tính idempotent

- Người thực hiện / thời gian: `claude-code-agent` / `2026-10-25T09:03+07:00`.
- Lệnh / thao tác: `cd backend; .venv\Scripts\python -m pytest -q`; script tạm chạy `normalize_markdown` hai lần trên 9 file cache Docling và bản processed.
- Kỳ vọng: không hồi quy; idempotent trên dữ liệu thật.
- Kết quả thực tế: **289 passed, 1 skipped**, 0 failed. Test mới: 39 (29 normalizer + 8 check_structure + 2 section_dominance). Idempotent trên cả 10 tài liệu.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- `test_bold_only_lines_become_headings` hỏng sau S-01 vì kỳ vọng cấp cũ. Đã cập nhật kỳ vọng (`HƯỚNG DẪN…` cấp 2) và chạy lại: đạt.
- Hai lần ingest cùng nội dung (cùng fingerprint `0a63b72686b2…`) cho kết quả vector khác nhau ở rank 5–10 (cov@10 0.850 so với 0.8525; hit@1/4/MRR không đổi), có thể do chỉ mục vector xấp xỉ được dựng lại. Chạy lại trên cùng index cho kết quả giống hệt (đã kiểm). Báo cáo commit là lần đo trên index cuối.
- Chưa chạy Ragas hay eval có sinh câu trả lời (ngoài phạm vi).
- Chưa đo theo nhóm tài liệu vì dataset chỉ có 1 nguồn và thiếu `source`.

## Kết luận

- Tiêu chí đã đạt: AC-01…AC-07 (AC-05 đúng biên 0.150; AC-06 chỉ đo được ở mức overall/nhóm hiện có).
- Tiêu chí chưa đạt/chưa xác minh: không có.
- Đề xuất: chuyển reviewer; người dùng quyết định commit.

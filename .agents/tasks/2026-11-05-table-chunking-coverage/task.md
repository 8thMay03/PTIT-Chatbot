# Task: Chunk bảng không làm mất dữ liệu (nhận diện bảng LlamaParse, ghép bảng ngắt trang, bảo toàn hàng)

- ID: `2026-11-05-table-chunking-coverage`
- Trạng thái: `in_review`
- Coordinator: `claude-code-agent`
- Người yêu cầu: người dùng (phiên Claude Code 2026-11-05: "bảng quá dài thì khi chunk hệ thống bỏ qua luôn làm sót mất dữ liệu quan trọng")
- Tạo lúc: `2026-11-05T22:30:22+07:00`
- Cập nhật lúc: `2026-11-05T23:42:51+07:00`

## Yêu cầu và kết quả mong muốn

Bảng dài trong tài liệu đã nạp bị chunk sai, người dùng hỏi về hàng trong bảng thì chatbot không tìm thấy. Điều tra ngày 2026-11-05 trên `data/datasets/*/Sổ tay sinh viên D26 _1_ _1_.md` (parse bằng LlamaParse, 3.653 hàng bảng còn lại sau cleaner):

1. **Nguyên nhân gốc — chunker không nhận ra bảng nào.** LlamaParse chạy với `compact_markdown_tables: True` (`backend/app/parsers/llamaparse.py:170`) nên dòng phân cách là `|-|-|-|`. `_starts_markdown_table` (`backend/app/ingestion/chunker.py:530`) đòi `:?-{3,}:?` ⇒ 0/424 bảng được nhận diện, toàn bộ bảng đi nhánh văn xuôi `_split_long_block`:
   - các hàng bị nối thành một dòng (đơn vị câu ghép bằng dấu cách);
   - hàng bị cắt giữa chừng tại `;`/`.` (vd. hàng 5.1 bảng điểm rèn luyện vắt qua 2 child, child sau bắt đầu "viện phân công làm lớp trưởng…|4 điểm|");
   - child sau không có header nên không biết giá trị thuộc cột nào; overlap câu chèn mảnh hàng trước vào đầu child.
   - Đo: 32 dòng hàng bị cắt dở, 2 hàng không còn nguyên vẹn trong bất kỳ child nào. Vá tạm regex thành `:?-+:?` (trong bộ nhớ) ⇒ 424 bảng, 0 hàng vỡ, 0 hàng mất, child lớn nhất 1.824 ký tự.
2. **Bảng ngắt trang.** LlamaParse nối các trang; một bảng dài thành nhiều bảng liền nhau lặp lại header, hoặc trang sau không có header (thành mảnh văn xuôi bắt đầu bằng `|`).
3. **Lỗi bảng HTML và cleaner** (tái hiện bằng dữ liệu tổng hợp; chưa gặp với output LlamaParse hiện tại nhưng sẽ gặp với Docling/DOCX):
   - `<tr>` thiếu `</tr>` ⇒ mất 120/120 hàng (`_HTML_TR` bắt buộc thẻ đóng);
   - nhiều `<tbody>` ⇒ chỉ lấy `<tbody>` đầu (`chunker.py:690`), mất 90/120 hàng;
   - `<tfoot>` (vd. hàng "Tổng cộng") và `<caption>` bị bỏ khi bảng bị tách;
   - bảng nằm ngay sau "MỤC LỤC" không có heading ngăn ⇒ cleaner bỏ cả bảng (`cleaner.py:117`).

Kết quả cần có: mọi hàng bảng sau cleaner nằm nguyên vẹn (không cắt giữa hàng) trong ít nhất một child, mỗi child chứa hàng bảng đều có header của bảng; có kiểm tra tự động chặn tái phát; index local được chunk lại và retrieval không thụt lùi.

## Phạm vi

- Bao gồm: `backend/app/ingestion/chunker.py`, `backend/app/ingestion/cleaner.py`, `backend/app/ingestion/pipeline.py` (chỉ log cảnh báo), `backend/scripts/check_chunks.py`, tests (`backend/tests/test_chunker*.py`, `backend/tests/test_check_chunks.py`, fixture mới trong `backend/tests/fixtures/`), báo cáo `documents/rag-eval/table-chunking/`, năm file task này.
- Ngoài phạm vi: đổi cấu hình LlamaParse (giữ `compact_markdown_tables`, chunker phải chịu được cả hai dạng), đổi `CHUNK_SIZE`/`CHILD_CHUNK_SIZE`, hybrid/rerank, prompt sinh câu trả lời, golden set `ptit_ragas_100.json`, sửa file trong `data/`, frontend.
- Ràng buộc:
  - Giữ tương thích bảng `| --- |` (Docling, fixture hiện có) — mọi test chunker hiện có phải xanh.
  - Không đổi schema DB / không cần migration; chunk lại qua luồng có sẵn (`POST /ingest/chunk`, `POST /datasets/{id}/chunk` hoặc `ingestion_pipeline.chunk_documents`), không dùng `delete_ingested_document`.
  - Không ghi đè `documents/rag-eval/baseline_*.json`, `rag-05/`, `rag-06/`, `rag-15/`.
  - Không ghi secret/nội dung `.env` vào nhật ký.

## Tiêu chí nghiệm thu

- [x] AC-01: Bảng Markdown có dòng phân cách 1–2 gạch (`|-|`, `|:-|--:|`) được nhận diện là bảng; trên file Sổ tay D26 số khối bảng nhận diện ≥ 400 và không còn mảnh bảng không header bị xử lý như văn xuôi (trừ mảnh không xác định được header, phải được liệt kê).
- [x] AC-02: Bất biến bảo toàn hàng: mọi hàng bảng (Markdown và HTML) còn lại sau `clean_text` xuất hiện nguyên vẹn trong ít nhất một child; không child nào chứa hàng bị cắt dở. Có test cho dữ liệu tổng hợp (bảng dài, bảng ngắt trang, hàng rất dài, HTML thiếu `</tr>`, nhiều `<tbody>`, `<tfoot>`) và kiểm tra trên file D26.
- [x] AC-03: Mọi child chứa hàng dữ liệu của bảng đều chứa dòng header (và dòng phân cách với Markdown / `<thead>` với HTML) của bảng đó.
- [x] AC-04: Bảng bị ngắt trang (các khối bảng liền kề cùng header, hoặc khối tiếp theo không header nhưng cùng số cột) được ghép thành một bảng logic trước khi tách; không sinh child chỉ có header hoặc mảnh < 3 hàng khi có thể gộp trong hard limit.
- [x] AC-05: `scripts.check_chunks` có mã lỗi mới cho hàng bảng bị vỡ/thiếu header (`--strict` trả 1 khi vi phạm); pipeline ghi cảnh báo khi tài liệu có nhiều dòng bắt đầu bằng `|` nhưng chunker không nhận ra bảng nào.
- [x] AC-06: Bảng ngay sau "MỤC LỤC" không bị cleaner bỏ nếu không phải bảng mục lục (hàng không kết thúc bằng số trang); bảng mục lục thật trong D26 vẫn bị lọc như hiện tại.
- [ ] AC-07: Sau khi chunk lại index local, hit@4 và MRR hybrid trên `ptit_ragas_100.json` không thấp hơn lần chạy baseline trên cùng index trước khi sửa; bộ câu hỏi về bảng mới (≥ 10 câu, fixture riêng) có hit@4 cao hơn baseline. → Kết quả: golden bm25 giữ nguyên, golden hybrid −0.01 (nhiễu 1 câu); bảng bm25/hybrid giữ nguyên (0.857/0.786). Vế cải thiện bảng chưa đạt — cần D-01 (task tiếp theo đã mở).
- [x] AC-08: Toàn bộ test backend xanh (782 passed, 1 skipped thực tế).

## Tài liệu và phụ thuộc

- Liên quan: RAG-06 `.agents/tasks/2026-10-25-rag06-article-clause-chunking/` (chunker theo Điều/Khoản, `check_chunks`), RAG-15 `.agents/tasks/2026-10-25-rag15-llamaparse-parser/` (bật `compact_markdown_tables`), task RAG-07 (bảng HTML) được nhắc nhưng chưa có thư mục task — task này bao phần lỗi bảng HTML gây mất dữ liệu.
- Script đo dùng khi điều tra (scratchpad phiên, không thuộc repo): `probe.py`, `coverage.py`, `verify_fix.py` — logic sẽ được chuyển thành test/`check_chunks`.
- Nhánh dự kiến: `feat/table-chunking-coverage` tách từ `dev` (hiện `14c4eb6`).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai S-01…S-07 trên nhánh `feat/table-chunking-coverage`
  (tách từ `dev` tại `14c4eb6`); 780 passed + 1 skipped toàn backend; 0 vi phạm
  bảng trên D26 (cả parse LlamaParse `.md` và Docling `.pdf`) và trên
  `check_chunks --data/--db`. Đã chunk lại index local (1.010 chunk) và đo
  retrieval trước/sau (xem `documents/rag-eval/table-chunking/`).
- Blocker: không có.
- AC-07 chưa đạt vế tăng hit@4 bảng (0.857→0.857 bm25, 0.786→0.786 hybrid —
  hàng đã nguyên vẹn nhưng chunk chứa hàng không vào top-k; cần D-01) và golden
  hybrid chênh 1 câu do nhiễu ngưỡng (0.830→0.820, cùng nội dung truy xuất).
  Task tiếp theo `2026-11-05-table-search-context` (D-01) đã mở theo quyết định
  có điều kiện của người dùng.
- Bước tiếp theo: reviewer tự review (self_review), xử lý nhận xét, verifier
  xác nhận V-01…V-08; coordinator kết luận (task ở `in_review`, chưa `done`
  vì AC-07 chưa đạt).

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-11-05T22:30:22+07:00` — `claude-code-agent`: tạo task từ kết quả điều tra. Chốt: (1) sửa chunker để chấp nhận dạng compact thay vì tắt `compact_markdown_tables` — không cần parse lại (tốn credit LlamaParse) và chunker phải chịu được cả hai dạng; (2) AC-07 so với baseline chạy lại trên cùng index ngay trước khi sửa, vì kho hiện tại khác kho lúc chạy `rag-06/`; (3) không sửa golden set, câu hỏi về bảng đặt trong fixture riêng.
- `2026-11-05T23:42:51+07:00` — người dùng duyệt: tạo nhánh mới từ `dev` (không dùng chung nhánh `feat/fix-chunk-pagination`); D-01 hoãn sang task tiếp theo (chỉ mở khi hit@4 bảng vẫn hụt — điều kiện đã xảy ra); D-02 đồng ý chunk lại + đo retrieval trên DB local.
